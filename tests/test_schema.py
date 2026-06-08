from edusim.database import SCHEMA


def test_schema_has_more_than_ten_tables():
    assert len(SCHEMA) >= 10


def test_schema_contains_users_and_roles():
    joined = "\n".join(SCHEMA)
    assert "CREATE TABLE IF NOT EXISTS users" in joined
    assert "CREATE TABLE IF NOT EXISTS roles" in joined
