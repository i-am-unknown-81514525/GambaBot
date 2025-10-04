--Init user
INSERT INTO holder_entity() VALUES () RETURNING id AS holder_id;
INSERT INTO user_acc(user_id, holder_id) VALUES (user_id, {holder_id});
INSERT INTO account(holder_id) VALUES ({holder_id}) RETURNING id AS account_id;
-- Py make_transaction(0, {account_id}, 0, 100, "Account creation")
