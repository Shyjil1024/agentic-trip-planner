from trip_planner import TripSession
from trip_planner.sqlite_storage import SQLiteTripSessionStore


def test_sqlite_store_persists_sessions_between_instances(tmp_path):
    database_path = tmp_path / "trip-planner.sqlite3"
    first_store = SQLiteTripSessionStore(database_path)
    first_store.create(TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh"))

    second_store = SQLiteTripSessionStore(database_path)
    loaded = second_store.get("trip-1")

    assert loaded is not None
    assert loaded.destination == "Ladakh"


def test_sqlite_store_updates_existing_session(tmp_path):
    store = SQLiteTripSessionStore(tmp_path / "trip-planner.sqlite3")
    store.create(TripSession(trip_id="trip-1", user_id="user-1", destination="Ladakh"))
    store.save(TripSession(trip_id="trip-1", user_id="user-1", destination="Leh"))

    assert store.get("trip-1").destination == "Leh"
