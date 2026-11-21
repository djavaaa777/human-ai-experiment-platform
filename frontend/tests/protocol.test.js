import test from 'node:test';
import assert from 'node:assert/strict';
import { initialSession, applyEvent, secondsRemaining } from '../src/protocol.js';

test('welcome restores identity, history and already submitted votes', () => {
  const state = applyEvent(initialSession, { type: 'welcome', player: 'B', voted_rounds: [1], messages: [{ id: 1, text: 'Hello' }] }, 0);
  assert.equal(state.player, 'B');
  assert.deepEqual(state.votedRounds, [1]);
  assert.equal(state.messages.length, 1);
});
test('only our vote acknowledgement locks our ballot', () => {
  const session = { ...initialSession, player: 'A' };
  assert.deepEqual(applyEvent(session, { type: 'vote_received', player: 'B', round: 1 }, 0).votedRounds, []);
  const voted = applyEvent(session, { type: 'vote_received', player: 'A', round: 1 }, 0);
  assert.deepEqual(applyEvent(voted, { type: 'vote_received', player: 'A', round: 1 }, 0).votedRounds, [1]);
});
test('history and live messages deduplicate by server ID', () => {
  let session = { ...initialSession, messages: [{ id: 1, text: 'Hello' }] };
  session = applyEvent(session, { type: 'chat', id: 1, text: 'Hello' }, 0);
  session = applyEvent(session, { type: 'chat', id: 2, text: 'Hi' }, 0);
  assert.equal(session.messages.length, 2);
});
test('countdown uses server remaining time without advancing phases locally', () => {
  const session = applyEvent(initialSession, { type: 'state', state: { phase: 'voting', round: 1, seconds_remaining: 5 } }, 1000);
  assert.equal(secondsRemaining(session, 3000), 3);
  assert.equal(secondsRemaining(session, 900), 5);
  assert.equal(secondsRemaining(session, 9000), 0);
  assert.equal(session.state.phase, 'voting');
  assert.equal(secondsRemaining(initialSession, 9000), null);
});
