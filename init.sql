CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL PRIMARY KEY,
    firstname           TEXT,
    lastname            TEXT,
    username            TEXT,
    chat_id             BIGINT,
    user_id             BIGINT,
    role                INTEGER,
    blocked             BOOLEAN,
    announce_allowed    BOOLEAN,
    last_announced      DATE,
    paid_requests_count BIGINT,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP,
    utm                 TEXT[],
    utm_created_at      TIMESTAMP,
    UNIQUE(user_id)
);
