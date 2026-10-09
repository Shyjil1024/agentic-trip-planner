from trip_planner.config import ProviderSettings
from trip_planner.live import SQLiteEventStore


def test_database_path_is_environment_configurable(monkeypatch):
    monkeypatch.setenv("TRIP_DATABASE_PATH", "data/custom.sqlite3")

    assert ProviderSettings.from_environment().database_path == "data/custom.sqlite3"


def test_sqlite_event_store_is_idempotent_across_instances(tmp_path):
    path = str(tmp_path / "events.sqlite3")
    first = SQLiteEventStore(path)
    second = SQLiteEventStore(path)

    assert first.mark_processed("event-1") is True
    assert second.mark_processed("event-1") is False
