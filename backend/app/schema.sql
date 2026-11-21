CREATE TABLE IF NOT EXISTS sessions (
    id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    config jsonb NOT NULL,
    ai_labels jsonb NOT NULL,
    phase text NOT NULL DEFAULT 'waiting',
    round integer NOT NULL DEFAULT 0 CHECK (round BETWEEN 0 AND 2),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'interrupted')),
    results jsonb
);
CREATE TABLE IF NOT EXISTS messages (
    session_id uuid NOT NULL REFERENCES sessions(id),
    id integer NOT NULL,
    player text NOT NULL CHECK (player IN ('A', 'B', 'C')),
    round integer NOT NULL CHECK (round IN (1, 2)),
    text text NOT NULL CHECK (length(text) BETWEEN 1 AND 1000),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, id)
);
CREATE TABLE IF NOT EXISTS votes (
    session_id uuid NOT NULL REFERENCES sessions(id),
    player text NOT NULL CHECK (player IN ('A', 'B', 'C')),
    round integer NOT NULL CHECK (round IN (1, 2)),
    target text NOT NULL CHECK (target IN ('A', 'B', 'C')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, player, round)
);
