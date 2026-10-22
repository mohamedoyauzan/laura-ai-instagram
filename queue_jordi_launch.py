"""Añade de forma idempotente las diez fotos iniciales de Jordi a la cola."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "jordi_launch_plan.json"
QUEUE_PATH = ROOT / "publication_queue.json"
BATCH_ID = "jordi-launch-2026-10-22"


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    existing = {
        row.get("launch_id")
        for row in queue
        if row.get("batch_id") == BATCH_ID
    }
    for item in plan:
        if item["id"] in existing:
            continue
        file_path = ROOT / item["file"]
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        queue.append(
            {
                "file": item["file"],
                "caption": item["caption"],
                "type": "photo",
                "batch_id": BATCH_ID,
                "launch_id": item["id"],
                "status": "pending",
            }
        )
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pending = [
        row["file"]
        for row in queue
        if row.get("batch_id") == BATCH_ID and row.get("status") != "published"
    ]
    print(json.dumps({"batch_id": BATCH_ID, "pending": pending}, ensure_ascii=False))


if __name__ == "__main__":
    main()
