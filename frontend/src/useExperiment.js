import { useEffect, useRef, useState } from 'react';
import { applyEvent, initialSession } from './protocol.js';

const TOKEN_KEY = 'group-decision.reconnect-token';

function storedToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export default function useExperiment() {
  const [token, setToken] = useState(storedToken);
  const [session, setSession] = useState(initialSession);
  const [status, setStatus] = useState('offline');
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);
  const [pending, setPending] = useState(null);
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const socketRef = useRef(null);
  const pendingRef = useRef(null);
  const joiningRef = useRef(false);

  function clearPending() { pendingRef.current = null; setPending(null); }

  useEffect(() => {
    if (!token) return;
    let disposed = false;
    let retry;
    let player;
    function connect() {
      setStatus('connecting');
      const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`);
      socketRef.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }));
      ws.onmessage = ({ data }) => {
        if (disposed) return;
        const event = JSON.parse(data);
        if (event.type === 'welcome') {
          player = event.player;
          clearPending();
          setError('');
        }
        if (event.type === 'state') {
          setStatus('connected');
          const action = pendingRef.current;
          if (action && (action.round !== event.state.round ||
            (action.type === 'chat' ? 'discussion' : 'voting') !== event.state.phase)) clearPending();
        }
        if (event.type === 'error') { setError(event.message); clearPending(); }
        if ((event.type === 'chat' || event.type === 'vote_received') && event.player === player) {
          clearPending();
        }
        setSession(current => applyEvent(current, event, performance.now()));
      };
      ws.onclose = ({ code }) => {
        if (disposed) return;
        clearPending();
        if (code === 4401) {
          setStatus('expired');
          setError('Your saved identity is no longer valid. The experiment may have restarted.');
        } else if (code === 4001) {
          setStatus('replaced');
          setError('This player is connected in another tab. Continue there or reconnect here.');
        } else {
          setStatus('reconnecting');
          retry = setTimeout(connect, 1500);
        }
      };
      ws.onerror = () => { /* onclose handles reconnects. */ };
    }
    connect();
    return () => {
      disposed = true;
      clearTimeout(retry);
      socketRef.current?.close();
    };
  }, [token, connectionAttempt]);

  async function join() {
    if (joiningRef.current) return;
    joiningRef.current = true;
    setJoining(true);
    setError('');
    try {
      // Check persistence before consuming a participant slot.
      localStorage.setItem('group-decision.storage-check', '1');
      localStorage.removeItem('group-decision.storage-check');
      const response = await fetch('/api/join', { method: 'POST' });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Could not join. Check that the server is running.');
      }
      const identity = await response.json();
      localStorage.setItem(TOKEN_KEY, identity.reconnect_token);
      setSession({ ...initialSession, player: identity.player, state: identity.state, receivedAt: performance.now() });
      setToken(identity.reconnect_token);
    } catch (err) {
      setError(`${err.message} If browser storage is disabled, enable it before joining.`);
    } finally {
      joiningRef.current = false;
      setJoining(false);
    }
  }

  function send(action) {
    if (status !== 'connected' || socketRef.current?.readyState !== WebSocket.OPEN || pendingRef.current) return false;
    pendingRef.current = action;
    setPending(action);
    setError('');
    socketRef.current.send(JSON.stringify(action));
    return true;
  }

  function forgetExpiredIdentity() {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* Current tab can still reset. */ }
    setToken(null);
    setSession(initialSession);
    setStatus('offline');
    setError('');
  }

  return { token, session, status, error, joining, pending, join, send,
    forgetExpiredIdentity, reconnect: () => setConnectionAttempt(value => value + 1) };
}
