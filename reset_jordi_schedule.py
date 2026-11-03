"""Reprograma una semana de Jordi usando medios ya revisados y públicos."""

from __future__ import annotations

import copy
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "jordi_automation_schedule.json"
TZ = ZoneInfo("Europe/Madrid")
START = date(2026, 11, 4)


def main() -> None:
    previous = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    source_days: dict[str, list[dict]] = {}
    for item in previous["items"]:
        source_days.setdefault(item["publish_at"][:10], []).append(item)
    templates = [source_days[key] for key in sorted(source_days)[:7]]
    if len(templates) != 7 or any(len(day) != 4 for day in templates):
        raise RuntimeError("No hay siete lotes completos ya revisados")

    items: list[dict] = []
    for offset, template in enumerate(templates):
        target_date = START + timedelta(days=offset)
        for item in template:
            new_item = copy.deepcopy(item)
            source_time = datetime.fromisoformat(item["publish_at"]).timetz().replace(tzinfo=None)
            new_item["id"] = f"auto-{target_date.isoformat()}-{item['kind']}-{source_time.strftime('%H%M')}"
            new_item["publish_at"] = datetime.combine(target_date, source_time, tzinfo=TZ).isoformat()
            new_item["status"] = "pending"
            new_item.pop("media_id", None)
            new_item.pop("published_at", None)
            new_item.pop("expired_at", None)
            if not (ROOT / new_item["file"]).is_file():
                raise RuntimeError(f"Falta el medio preparado: {new_item['file']}")
            items.append(new_item)

    output = {
        "version": 2,
        "timezone": "Europe/Madrid",
        "account_username": "jordi_fitt",
        "generated_at": datetime.now(TZ).isoformat(),
        "items": items,
    }
    SCHEDULE.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"days": 7, "items": len(items), "first": items[0]["publish_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
