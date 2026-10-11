"""Create and seed both project databases deterministically."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from data.models import cultpass, udahub


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_DB = SOLUTION_ROOT / "data" / "external" / "cultpass.db"
DEFAULT_CORE_DB = SOLUTION_ROOT / "data" / "core" / "udahub.db"
SEED_TIME = datetime(2026, 1, 1, 12, 0, 0)


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def setup_external_database(path: Path = DEFAULT_EXTERNAL_DB) -> Path:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    cultpass.Base.metadata.create_all(engine)

    users = _load_jsonl(SOLUTION_ROOT / "data" / "external" / "cultpass_users.jsonl")
    experiences = _load_jsonl(SOLUTION_ROOT / "data" / "external" / "cultpass_experiences.jsonl")
    statuses = ["active", "active", "active", "cancelled", "active", "paused"]
    tiers = ["premium", "basic", "premium", "basic", "premium", "basic"]

    with Session(engine) as session:
        for item in users:
            session.add(
                cultpass.User(
                    user_id=item["id"],
                    full_name=item["name"],
                    email=item["email"],
                    is_blocked=item["is_blocked"],
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                )
            )
        for index, item in enumerate(experiences, start=1):
            session.add(
                cultpass.Experience(
                    experience_id=f"exp-{index:03d}",
                    title=item["title"],
                    description=item["description"],
                    location=item["location"],
                    when=SEED_TIME + timedelta(days=index * 7),
                    slots_available=5 + index,
                    is_premium=index % 2 == 1,
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                )
            )
        for index, item in enumerate(users):
            session.add(
                cultpass.Subscription(
                    subscription_id=f"sub-{index + 1:03d}",
                    user_id=item["id"],
                    status=statuses[index],
                    tier=tiers[index],
                    monthly_quota=4,
                    started_at=SEED_TIME - timedelta(days=90),
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                )
            )
        # Multiple users have reservations so lookup behavior is demonstrable.
        reservations = [
            ("res-001", users[0]["id"], "exp-001", "reserved"),
            ("res-002", users[0]["id"], "exp-004", "reserved"),
            ("res-003", users[1]["id"], "exp-002", "reserved"),
            ("res-004", users[2]["id"], "exp-006", "cancelled"),
        ]
        for reservation_id, user_id, experience_id, status in reservations:
            session.add(
                cultpass.Reservation(
                    reservation_id=reservation_id,
                    user_id=user_id,
                    experience_id=experience_id,
                    status=status,
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                )
            )
        session.commit()
    return path


def setup_core_database(path: Path = DEFAULT_CORE_DB) -> Path:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    udahub.Base.metadata.create_all(engine)

    users = _load_jsonl(SOLUTION_ROOT / "data" / "external" / "cultpass_users.jsonl")
    articles = _load_jsonl(SOLUTION_ROOT / "data" / "external" / "cultpass_articles.jsonl")
    if len(articles) < 14:
        raise AssertionError("The knowledge base must contain at least 14 articles")

    with Session(engine) as session:
        session.add(udahub.Account(account_id="cultpass", account_name="CultPass Card"))
        for item in users:
            session.add(
                udahub.User(
                    user_id=f"core-{item['id']}",
                    account_id="cultpass",
                    external_user_id=item["id"],
                    user_name=item["name"],
                )
            )
        for index, article in enumerate(articles, start=1):
            session.add(
                udahub.Knowledge(
                    article_id=article.get("article_id", f"kb-{index:03d}"),
                    account_id="cultpass",
                    title=article["title"],
                    content=article["content"],
                    tags=article["tags"],
                )
            )
        session.commit()
    return path


def setup_all(external_db: Path = DEFAULT_EXTERNAL_DB, core_db: Path = DEFAULT_CORE_DB) -> tuple[Path, Path]:
    return setup_external_database(external_db), setup_core_database(core_db)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-db", type=Path, default=DEFAULT_EXTERNAL_DB)
    parser.add_argument("--core-db", type=Path, default=DEFAULT_CORE_DB)
    args = parser.parse_args()
    external, core = setup_all(args.external_db, args.core_db)
    print(f"Created CultPass database: {external}")
    print(f"Created UDA-Hub database: {core}")
    print("Loaded 6 users, 7 experiences, 4 reservations, and 16 knowledge articles.")


if __name__ == "__main__":
    main()
