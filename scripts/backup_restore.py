"""Disaster recovery and automated backup utility for Task API database.
Supports JSON table snapshot and restore across SQLite and PostgreSQL engines.
"""
import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add app directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
app_dir = root_dir / "app"
sys.path.insert(0, str(app_dir))

import models
from database import SessionLocal


def backup_to_json(output_path: Path) -> int:
    print(f"Starting database backup to {output_path}...")
    session = SessionLocal()
    try:
        tasks = session.query(models.Task).all()
        records = []
        for t in tasks:
            records.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "completed": t.completed,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "tags": t.tags,
                "is_deleted": t.is_deleted,
                "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            })

        output_path.parent.mkdir(parents=True, exist_ok=True)
        backup_metadata = {
            "version": "1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "record_count": len(records),
            "records": records,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(backup_metadata, f, indent=2)

        print(f"Successfully backed up {len(records)} tasks to {output_path}")
        return len(records)
    finally:
        session.close()


def restore_from_json(input_path: Path, clear_existing: bool = False) -> int:
    if not input_path.exists():
        print(f"Error: backup file {input_path} does not exist.")
        return 0

    print(f"Restoring database from {input_path} (clear_existing={clear_existing})...")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    session = SessionLocal()
    try:
        if clear_existing:
            session.query(models.Task).delete()
            session.commit()

        restored = 0
        for r in records:
            task = models.Task(
                id=r.get("id"),
                title=r["title"],
                description=r.get("description"),
                completed=r.get("completed", False),
                status=r.get("status", "pending"),
                priority=r.get("priority", "medium"),
                due_date=datetime.fromisoformat(r["due_date"]) if r.get("due_date") else None,
                tags=r.get("tags", ""),
                is_deleted=r.get("is_deleted", False),
                deleted_at=datetime.fromisoformat(r["deleted_at"]) if r.get("deleted_at") else None,
            )
            session.merge(task)
            restored += 1

        session.commit()
        print(f"Successfully restored {restored} records from {input_path}")
        return restored
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task API Backup & Restore Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Snapshot database into JSON file")
    backup_parser.add_argument(
        "--output",
        type=Path,
        default=root_dir / "backups" / f"backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json",
    )

    restore_parser = subparsers.add_parser("restore", help="Restore database from JSON snapshot")
    restore_parser.add_argument("--input", type=Path, required=True, help="Path to backup JSON file")
    restore_parser.add_argument(
        "--clear", action="store_true", help="Clear existing records before restoring"
    )

    args = parser.parse_args()
    if args.command == "backup":
        backup_to_json(args.output)
    elif args.command == "restore":
        restore_from_json(args.input, args.clear)
