"""Ingest a document into the knowledge base (F15).
Usage:
  python scripts/ingest_knowledge.py FILE.(md|txt|pdf) --id KB-X --title "..." --publisher "..." --topic heat_stress --url https://... \
         [--crop paddy] [--stage flowering] [--region "Andhra Pradesh"] [--date 2024-05-01] [--status verified|needs_review]
  python scripts/ingest_knowledge.py --seed          # (re)load knowledge/metadata/*.json
  python scripts/ingest_knowledge.py --outdate KB-X  # mark a document outdated (excluded from retrieval)
Documents default to needs_review: only mark `verified` after a qualified person has checked the source."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.db import init_db  # noqa: E402
from app.services import knowledge_service as ks  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("file", nargs="?")
p.add_argument("--seed", action="store_true")
p.add_argument("--outdate")
for a in ("id", "title", "publisher", "topic", "url", "crop", "stage", "region", "date"):
    p.add_argument(f"--{a}")
p.add_argument("--status", default="needs_review", choices=["verified", "needs_review"])
a = p.parse_args()
init_db()
if a.seed:
    print("seeded", ks.seed_from_metadata_dir(), "documents")
elif a.outdate:
    print("outdated" if ks.mark_outdated(a.outdate) else "not found")
elif a.file:
    meta = {"document_id": a.id, "title": a.title, "publisher": a.publisher, "topic": a.topic, "source_url": a.url, "crop_id": a.crop, "growth_stage_id": a.stage, "region": a.region,
            "publication_date": a.date, "retrieved_at": datetime.now(timezone.utc).isoformat(), "verification_status": a.status}
    print("chunks:", ks.ingest_file(Path(a.file), meta))
else:
    p.print_help()
