from uuid import uuid4

from seed.fixtures import DETECTION_RUNS, FLAGGED_ACCOUNTS


def list_runs() -> list[dict[str, object]]:
    return [run.model_dump() for run in DETECTION_RUNS]


def queue_run() -> dict[str, str]:
    return {
        "run_id": str(uuid4()),
        "status": "queued",
        "message": "Detection run queued for worker execution",
    }


def get_results() -> list[dict[str, object]]:
    return [item.model_dump() for item in FLAGGED_ACCOUNTS]
