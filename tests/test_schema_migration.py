from sqlalchemy import create_engine, text

from cogn_os.storage.database import ensure_sqlite_schema


def test_ensure_sqlite_schema_adds_missing_context_timeline_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE context_timeline (id INTEGER PRIMARY KEY)"))

    ensure_sqlite_schema(engine)

    with engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(context_timeline)"))]
    assert "summary" in columns
    assert "payload_json" in columns
