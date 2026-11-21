import { useEffect, useRef, useState } from 'react';
import useExperiment from './useExperiment.js';
import { secondsRemaining } from './protocol.js';

const names = { waiting: 'Waiting Room', discussion: 'Discussion Chat', voting: 'Voting', finished: 'Final Results' };

function Transcript({ messages, player }) {
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [messages.length]);
  return <div className="transcript" role="log" aria-label="Discussion messages" aria-live="polite">
    {!messages.length && <p className="muted">No messages yet. Share your suggestion with the group.</p>}
    {messages.map(message => <article className={`message ${message.player === player ? 'mine' : ''}`} key={message.id}>
      <div className="message-meta"><strong>Player {message.player}{message.player === player ? ' (you)' : ''}</strong><span>Round {message.round}</span></div>
      <p>{message.text}</p>
    </article>)}
    <div ref={end} />
  </div>;
}

export default function App() {
  const experiment = useExperiment();
  const { session, token, status, error, pending } = experiment;
  const { player, state, messages, votedRounds } = session;
  const [now, setNow] = useState(performance.now());
  const [draft, setDraft] = useState('');
  const [target, setTarget] = useState('');
  useEffect(() => {
    const timer = setInterval(() => setNow(performance.now()), 200);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => { setTarget(''); setDraft(''); }, [state?.round, state?.phase]);
  const remaining = secondsRemaining(session, now);
  const connected = status === 'connected';
  const canAct = connected && remaining > 0 && !pending;
  const voted = votedRounds.includes(state?.round);
  const phase = state?.phase;
  const timeLabel = remaining == null ? null : `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`;

  function sendChat(event) {
    event.preventDefault();
    if (canAct && phase === 'discussion' && draft.trim() && experiment.send({ type: 'chat', text: draft.trim(), round: state.round })) setDraft('');
  }
  function vote(event) {
    event.preventDefault();
    if (canAct && phase === 'voting' && !voted && target) experiment.send({ type: 'vote', target, round: state.round });
  }

  return <main className="shell">
    <header className="page-header"><div><p className="eyebrow">Center for Humans and Machines</p><h1>Group Decision Experiment</h1></div>
      {player && <span className="identity">Player {player}</span>}
    </header>
    {error && <div role="alert" className="notice error">{error}</div>}
    {token && !connected && <div className="notice" role="status">
      {status === 'expired' ? <button onClick={experiment.forgetExpiredIdentity}>Clear expired identity</button>
        : status === 'replaced' ? <button onClick={experiment.reconnect}>Reconnect here</button>
          : 'Connecting to the experiment… Actions will be available when connected.'}
    </div>}

    {!token ? <section className="panel join">
      <p className="eyebrow">Three players · Two rounds · One decision</p>
      <h2>Join Experiment</h2>
      <p>Discuss who should be the Decision Maker, then cast your vote after each round. You may vote for any player, including yourself.</p>
      <p className="muted">You’ll receive an anonymous player name. Your identity is saved in this browser so you can return after a refresh.</p>
      <button onClick={experiment.join} disabled={experiment.joining}>{experiment.joining ? 'Joining…' : 'Join Experiment'}</button>
    </section> : state && <section className="panel">
      <div className="phase-header"><div><p className="eyebrow">{phase === 'waiting' ? 'Getting ready' : phase === 'finished' ? 'Experiment complete' : `Round ${state.round} of 2`}</p><h2>{names[phase]}</h2></div>
        {timeLabel && <div className="timer"><span>Time remaining</span><strong aria-label={`${remaining} seconds remaining`}>{timeLabel}</strong></div>}
      </div>
      {phase === 'waiting' && <><p>You’re in, Player {player}. Please wait for the group to be ready.</p><p className="muted">The discussion will start automatically. Keep this page open.</p><div className="players">{state.players.map(label => <span key={label}>Player {label}{label === player ? ' (you)' : ''}</span>)}</div></>}
      {phase === 'discussion' && <>
        <p>Who should be the Decision Maker? Share your suggestion with the group.</p>
        <Transcript messages={messages} player={player} />
        <form onSubmit={sendChat} className="chat-form">
          <label htmlFor="message">Your message</label>
          <textarea id="message" value={draft} onChange={e => setDraft(e.target.value)} maxLength={1000} rows={3} disabled={!connected || remaining === 0} placeholder="Share a short message…" />
          <div className="form-footer"><span className="muted">{draft.length}/1000</span><button disabled={!canAct || !draft.trim()}>{pending?.type === 'chat' ? 'Sending…' : 'Send message'}</button></div>
        </form>
      </>}
      {phase === 'voting' && <>
        <p>Select your Decision Maker. You have one vote this round; a submitted vote cannot be changed.</p>
        <form onSubmit={vote}>
          <fieldset disabled={!canAct || voted}><legend>Choose a player</legend><div className="vote-options">{state.players.map(label => <label className={target === label ? 'selected' : ''} key={label}>
            <input type="radio" name="candidate" value={label} checked={target === label} onChange={() => setTarget(label)} />Player {label}{label === player ? ' (you)' : ''}
          </label>)}</div></fieldset>
          <button disabled={!canAct || voted || !target}>{voted ? 'Vote recorded' : pending?.type === 'vote' ? 'Submitting…' : 'Submit vote'}</button>
        </form>
        {voted && <p className="success" role="status">Your vote is recorded. Waiting for the round to end.</p>}
        <details><summary>Review discussion</summary><Transcript messages={messages} player={player} /></details>
      </>}
      {phase === 'finished' && state.results && <>
        <div className="winner"><p>Selected Decision Maker</p><h3>Player {state.results.winner}</h3></div>
        <table><caption>Combined votes from both rounds</caption><thead><tr><th scope="col">Player</th><th scope="col">Votes</th></tr></thead><tbody>{state.players.map(label => <tr key={label}><th scope="row">Player {label}{label === player ? ' (you)' : ''}</th><td>{state.results.totals[label]}</td></tr>)}</tbody></table>
        <p className="muted">Ties are resolved alphabetically by player name. Missing votes count as abstentions.</p>
        <p>Thank you for participating.</p>
      </>}
      {remaining === 0 && phase !== 'finished' && <p role="status" className="muted">Time is up. Waiting for the server’s next phase…</p>}
    </section>}
    <footer>Two discussion rounds, each followed by a private vote.</footer>
  </main>;
}
