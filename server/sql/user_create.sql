--Init user
INSERT INTO holder_entity() VALUES () RETURNING id;
INSERT INTO user(id, holder_id) VALUES (user_id, {holder_id});
