"""FastAPI transport; session rules remain in engine.py."""

import asyncio
from contextlib import asynccontextmanager, suppress
import json
import os
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from .config import load_config
from .engine import ExperimentError, ExperimentSession
from .session import SessionHub
from .storage import PostgresStore, PersistenceError


class StrictMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Auth(StrictMessage):
    type: Literal["auth"]
    token: str = Field(min_length=1, max_length=128)


class Chat(StrictMessage):
    type: Literal["chat"]
    text: str = Field(min_length=1, max_length=1000)
    round: int = Field(ge=1, le=2)


class Vote(StrictMessage):
    type: Literal["vote"]
    target: Literal["A", "B", "C"]
    round: int = Field(ge=1, le=2)


ACTION = TypeAdapter(Annotated[Chat | Vote, Field(discriminator="type")])


async def receive_payload(socket: WebSocket) -> dict:
    frame = await socket.receive()
    if frame["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(frame.get("code", 1000))
    text = frame.get("text")
    if text is None or len(text) > 8192:
        raise ValueError("Expected a JSON text message under 8192 characters")
    return json.loads(text)


async def deliver(socket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        event = await queue.get()
        if "_close" in event:
            await socket.close(code=event["_close"])
            return
        await asyncio.wait_for(socket.send_json(event), timeout=5)


def create_app(config=None, *, clock=monotonic, tick_seconds=0.25, store_factory=PostgresStore.from_environment, static_dir=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        settings = config or load_config(os.getenv("CONFIG_PATH", Path(__file__).resolve().parents[2] / "config.yml"))
        store = store_factory()
        engine = ExperimentSession(settings, clock=clock)
        if store is not None:
            try:
                store.start(settings, engine.ai_labels())
            except BaseException:
                store.close()
                raise
        hub = SessionHub(engine, store=store)
        app.state.hub = hub

        async def ticker():
            while True:
                await asyncio.sleep(tick_seconds)
                try:
                    hub.tick()
                except PersistenceError:
                    return  # Health becomes 503; restart is required, no silent data loss.

        task = asyncio.create_task(ticker())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            if store is not None:
                store.close()

    app = FastAPI(title="Group decision experiment", lifespan=lifespan)

    @app.get("/health")
    async def health():
        hub = app.state.hub
        if hub.failed or (hub.store is not None and not hub.store.healthy()):
            raise HTTPException(status_code=503, detail="Database unavailable")
        if hub.store is not None:
            return {"status": "ok", "database": "ok"}
        return {"status": "ok"}

    @app.post("/api/join", status_code=201, include_in_schema=False)
    @app.post("/join", status_code=201)
    async def join(response: Response):
        response.headers["Cache-Control"] = "no-store"
        try:
            return app.state.hub.join()
        except ExperimentError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PersistenceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.websocket("/ws")
    async def websocket(socket: WebSocket):
        hub = app.state.hub
        await socket.accept()
        # Credentials travel in the first frame, not URLs/access logs.
        try:
            auth = Auth.model_validate(await asyncio.wait_for(receive_payload(socket), timeout=10))
            player = hub.authenticate(auth.token)
            if player is None:
                await socket.close(code=4401)
                return
        except (ValueError, asyncio.TimeoutError):
            await socket.close(code=4401)
            return
        except WebSocketDisconnect:
            return

        try:
            queue = hub.connect(player)
        except PersistenceError:
            await socket.close(code=1011)
            return
        writer = asyncio.create_task(deliver(socket, queue))

        async def receive_actions():
            while True:
                try:
                    payload = await receive_payload(socket)
                    if not hub.is_current(player, queue):
                        return
                    action = ACTION.validate_python(payload)
                    hub.handle(player, action)
                except (ValidationError, ValueError) as exc:
                    message = str(exc) if isinstance(exc, ExperimentError) else "Invalid message format"
                    hub.send(queue, {"type": "error", "message": message})
                    hub.send(queue, hub.state_event())

        reader = asyncio.create_task(receive_actions())
        try:
            done, _ = await asyncio.wait((reader, writer), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (WebSocketDisconnect, OSError, asyncio.TimeoutError, PersistenceError):
            pass
        finally:
            hub.disconnect(player, queue)
            for task in (reader, writer):
                task.cancel()
            await asyncio.gather(reader, writer, return_exceptions=True)
            with suppress(RuntimeError, OSError):
                await socket.close()

    assets = Path(static_dir or os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
    if assets.is_dir():
        # Last route: API and WebSocket endpoints take precedence.
        app.mount("/", StaticFiles(directory=assets, html=True), name="frontend")
    return app


app = create_app()
