import json
from pathlib import Path
from graph.retrieval_config import TRACE_FILE


def write_trace(record: dict) -> None:
    """
    Appends one JSON line to TRACE_FILE.
    Creates the destination directory if it does not exist.
    Catches all exceptions to ensure it never raises.
    """
    try:
        path = Path(TRACE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass
