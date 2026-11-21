export const initialSession = {
  player: null, state: null, receivedAt: 0, messages: [], votedRounds: [],
};

export function applyEvent(session, event, now) {
  switch (event.type) {
    case 'welcome':
      return { ...session, player: event.player, messages: event.messages,
        votedRounds: event.voted_rounds };
    case 'state':
      return { ...session, state: event.state, receivedAt: now };
    case 'chat':
      return { ...session, messages: [...new Map(
        [...session.messages, event].map(message => [message.id, message]),
      ).values()].sort((a, b) => a.id - b.id).slice(-100) };
    case 'vote_received':
      return event.player === session.player
        ? { ...session, votedRounds: [...new Set([...session.votedRounds, event.round])] }
        : session;
    default:
      return session;
  }
}

export function secondsRemaining(session, now) {
  const seconds = session.state?.seconds_remaining;
  return seconds == null ? null : Math.max(0, Math.ceil(seconds - Math.max(0, now - session.receivedAt) / 1000));
}
