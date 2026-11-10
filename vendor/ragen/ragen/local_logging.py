"""Local experiment evidence, independent of external tracking accounts."""
import dataclasses
import json
import math
import os
from pathlib import Path
import time


def plain(value):
    if dataclasses.is_dataclass(value):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if hasattr(value, "tolist"):
        return plain(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def append_record(filename, record):
    directory = os.environ.get("RAGEN_OUTPUT_DIR")
    if not directory:
        return
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(plain(record), ensure_ascii=False, allow_nan=False) + "\n")


def log_metrics(step, metrics):
    append_record("metrics.jsonl", {"step": step, "timestamp": time.time(), **metrics})


def log_validation(step, validation_batch, manager):
    for cache, env in zip(manager.rollout_cache, manager.envs):
        append_record("validation_trajectories.jsonl", {
            "step": step,
            "validation_batch": validation_batch,
            "seed": env["status"].seed,
            "status": env["status"],
            **cache,
        })
