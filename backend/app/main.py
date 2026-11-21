"""FastAPI transport; session rules remain in engine.py."""

import asyncio
from contextlib import asynccontextmanager, suppress
import json
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from .config import load_config
from .engine import ExperimentError, ExperimentSession
from .session import SessionHub


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


def create_app(config=None, *, clock=monotonic, tick_seconds=0.25) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        settings = config or load_config(Path(__file__).resolve().parents[2] / "config.yml")
        hub = SessionHub(ExperimentSession(settings, clock=clock))
        app.state.hub = hub

        async def ticker():
            while True:
                await asyncio.sleep(tick_seconds)
                hub.engine.tick()
                hub.broadcast_state()

        task = asyncio.create_task(ticker())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Group decision experiment", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/join", status_code=201)
    async def join(response: Response):
        response.headers["Cache-Control"] = "no-store"
        try:
            return app.state.hub.join()
        except ExperimentError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

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

        queue = hub.connect(player)
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
        except (WebSocketDisconnect, OSError, asyncio.TimeoutError):
            pass
        finally:
            hub.disconnect(player, queue)
            for task in (reader, writer):
                task.cancel()
            await asyncio.gather(reader, writer, return_exceptions=True)
            with suppress(RuntimeError, OSError):
                await socket.close()

    return app


app = create_app()
