from datetime import datetime

from watchx.models import CommandResult, Frame
from watchx.store import RunStore, open_store


def test_run_store_records_invocations(tmp_path) -> None:
    path = tmp_path / "watchx.db"
    store = RunStore(path, "echo ok")
    store.record(Frame(CommandResult("ok", "", 0, 1.5, datetime.now()), ("ok",), 1))
    run_id = store.run_id
    store.close()

    with open_store(path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM invocations WHERE run_id = ?", (run_id,)
        ).fetchone()[0]

    assert count == 1
