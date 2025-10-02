CREATE TABLE IF NOT EXISTS holder_entity(
    holder_id INT PRIMARY KEY AUTOINCREMENT,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
);

CREATE TABLE IF NOT EXISTS user_acc(
    user_id BIGINT PRIMARY KEY,
    holder_id INT NOT NULL,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (holder_id) REFERENCES holder_entity(holder_id)
);

CREATE TABLE IF NOT EXISTS jwt_token(
    user_id BIGINT NOT NULL PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_acc(user_id)
);

CREATE TABLE IF NOT EXISTS account(
    id BIGINT PRIMARY KEY,
    holder_id INT NOT NULL,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (holder_id) REFERENCES holder_entity(holder_id)
);

CREATE TABLE IF NOT EXISTS coin(
    id INT PRIMARY KEY AUTOINCREMENT,
    unique_name TEXT NOT NULL UNIQUE,
    read_name TEXT NOT NULL,
);

CREATE TABLE IF NOT EXISTS user_coin(
    user_id INT NOT NULL,
    coin_id INT NOT NULL,
    amount BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, coin_id),
    FOREIGN KEY (user_id) REFERENCES account(id),
    FOREIGN KEY (coin_id) REFERENCES coin(id),
);

CREATE TABLE IF NOT EXISTS game_instance(
    game_id TEXT PRIMARY KEY,
    game_secret TEXT NOT NULL,
    game_hash TEXT NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT 0,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uni_transact(
    id INT PRIMARY KEY AUTOINCREMENT,
    src BIGINT NOT NULL,
    dst BIGINT NOT NULL,
    coin_id INT NOT NULL,
    amount BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL,
    inner_hash TEXT NOT NULL,
    reason TEXT NOT NULL,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transact_data TEXT GENERATED ALWAYS AS (
        CAST(src AS TEXT) || '--' ||
        CAST(dst AS TEXT) || '--' ||
        CAST(coin_id AS TEXT) || '--' ||
        CAST(amount AS TEXT) || '--' ||
        kind || '--' ||
        inner_hash || '--' ||
        STRFTIME("%Y-%m-%d %H:%M:%S", created_at) || '--' ||
        reason
    ),
    FOREIGN KEY (coin_id) REFERENCES coin(id),
    FOREIGN KEY (src) REFERENCES account(id),
    FOREIGN KEY (dst) REFERENCES account(id),
    CONSTRAINT kind_check CHECK (kind == "reward" || kind == "game" || kind == "none")
);

CREATE TABLE IF NOT EXISTS transact_chain(
    tx TEXT NOT NULL PRIMARY KEY,
    transact_id INT NOT NULL UNIQUE,
    FOREIGN KEY (transact_id) REFERENCES uni_transact(id)
);

CREATE TABLE IF NOT EXISTS reward_transact(
    ref_id INT UNIQUE,
    reason TEXT NOT NULL,
    transact_data TEXT GENERATED ALWAYS AS (
        reason
    ),
    FOREIGN KEY ref_id REFERENCES uni_transact(ref_id)
);

CREATE TABLE IF NOT EXISTS game_transact(
    ref_id INT UNIQUE,
    server_secret TEXT UNIQUE NOT NULL,
    client_secret TEXT UNIQUE NOT NULL,
    transact_data TEXT GENERATED ALWAYS AS (
        server_secret || '--' || client_secret
    ),
    user_win BOOLEAN NOT NULL,
    FOREIGN KEY ref_id REFERENCES uni_transact(ref_id)
);
