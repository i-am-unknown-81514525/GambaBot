CREATE TABLE IF NOT EXISTS holder_entity(
    holder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    custom_name TEXT NULL DEFAULT NULL,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_acc(
    user_id BIGINT PRIMARY KEY,
    holder_id INT NOT NULL UNIQUE,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holder_id INT NOT NULL,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (holder_id) REFERENCES holder_entity(holder_id)
);

CREATE TABLE IF NOT EXISTS coin(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_name TEXT NOT NULL UNIQUE,
    read_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_coin(
    account_id INT NOT NULL,
    coin_id INT NOT NULL,
    amount BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (account_id, coin_id),
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (coin_id) REFERENCES coin(id)
);

CREATE TABLE IF NOT EXISTS game_instance(
    game_id TEXT PRIMARY KEY,
    game_secret TEXT NOT NULL,
    game_hash TEXT NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT 0,
    create_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uni_transact(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src INT NOT NULL,
    dst INT NOT NULL,
    coin_id INT NOT NULL,
    amount BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL,
    inner_hash TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT 'No reason',
    created_dt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transact_data TEXT GENERATED ALWAYS AS (
        CAST(src AS TEXT) || '--' ||
        CAST(dst AS TEXT) || '--' ||
        CAST(coin_id AS TEXT) || '--' ||
        CAST(amount AS TEXT) || '--' ||
        kind || '--' ||
        inner_hash || '--' ||
        STRFTIME('%Y-%m-%d %H:%M:%S', created_dt) || '--' ||
        reason
    ),
    FOREIGN KEY (coin_id) REFERENCES coin(id),
    FOREIGN KEY (src) REFERENCES account(id),
    FOREIGN KEY (dst) REFERENCES account(id),
    CONSTRAINT kind_check CHECK (kind == 'reward' OR kind == 'game' OR kind == 'none')
);

CREATE TABLE IF NOT EXISTS transact_chain(
    order_op INTEGER PRIMARY KEY AUTOINCREMENT,
    tx TEXT NOT NULL UNIQUE,
    transact_id INT NOT NULL UNIQUE,
    FOREIGN KEY (transact_id) REFERENCES uni_transact(id)
);

CREATE TABLE IF NOT EXISTS reward_transact(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id INT UNIQUE NULL REFERENCES uni_transact(id),
    reason TEXT NOT NULL,
    transact_data TEXT GENERATED ALWAYS AS (
        reason
    )
);

CREATE TABLE IF NOT EXISTS game_transact(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id INT UNIQUE NULL REFERENCES uni_transact(id),
    server_secret TEXT UNIQUE NOT NULL,
    client_secret TEXT UNIQUE NOT NULL,
    game_instance TEXT UNIQUE NOT NULL REFERENCES game_instance(game_id),
    transact_data TEXT GENERATED ALWAYS AS (
        game_instance || '--' ||server_secret || '--' || client_secret
    ),
    user_win BOOLEAN NOT NULL
);

INSERT INTO holder_entity (holder_id, custom_name) VALUES (0, 'SYSTEM');
INSERT INTO user_acc(user_id, holder_id) VALUES (0, 0);
INSERT INTO account(id, holder_id) VALUES (0, 0);
INSERT INTO holder_entity (holder_id, custom_name) VALUES (-1, 'RESERVED');
INSERT INTO user_acc(user_id, holder_id) VALUES (-1, -1);
INSERT INTO account(id, holder_id) VALUES (-1, -1);
INSERT INTO coin(id, unique_name, read_name) VALUES (0, 'COIN', 'Coin');
INSERT INTO user_coin(account_id, coin_id, amount) VALUES (0, 0, 21000000000);
INSERT INTO user_coin(account_id, coin_id, amount) VALUES (-1, 0, 0);
