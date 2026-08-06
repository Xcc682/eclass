import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.points import PointTransaction
from app.models.user import User


POINT_RULE_VERSION = "2026.1"
POINT_MODULES = ("interview", "debate", "history", "tour")
POINT_LEDGER_MODULES = (*POINT_MODULES, "community")
MODULE_LABELS = {
    "interview": "入党谈话",
    "debate": "思政辩论",
    "history": "党史情景",
    "tour": "红色研学",
    "community": "成长社区",
    "system": "历史余额",
}


def award_points(
    db: Session,
    user: User,
    *,
    module: str,
    event_type: str,
    source_id: str,
    points: int,
    description: str,
    metadata: dict[str, Any] | None = None,
    rule_version: str = POINT_RULE_VERSION,
) -> tuple[PointTransaction, bool]:
    """Create one point event and atomically update the cached balance.

    The unique source key makes retries and concurrent completion requests
    idempotent. Callers own the outer transaction and commit lifecycle.
    """
    existing = db.scalar(select(PointTransaction).where(
        PointTransaction.user_id == user.id,
        PointTransaction.module == module,
        PointTransaction.event_type == event_type,
        PointTransaction.source_id == str(source_id),
    ))
    if existing:
        return existing, False

    transaction = PointTransaction(
        user_id=user.id,
        module=module,
        event_type=event_type,
        source_id=str(source_id),
        points=int(points),
        rule_version=rule_version,
        description=description,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    try:
        with db.begin_nested():
            db.add(transaction)
            db.flush()
    except IntegrityError:
        winner = db.scalar(select(PointTransaction).where(
            PointTransaction.user_id == user.id,
            PointTransaction.module == module,
            PointTransaction.event_type == event_type,
            PointTransaction.source_id == str(source_id),
        ))
        if winner:
            return winner, False
        raise

    db.execute(
        update(User)
        .where(User.id == user.id)
        .values(total_points=User.total_points + int(points))
    )
    db.flush()
    db.expire(user, ["total_points"])
    return transaction, True


def point_summary(db: Session, user: User, limit: int = 20) -> dict[str, Any]:
    rows = db.execute(
        select(PointTransaction.module, func.coalesce(func.sum(PointTransaction.points), 0))
        .where(PointTransaction.user_id == user.id)
        .group_by(PointTransaction.module)
    ).all()
    by_module = {module: 0 for module in (*POINT_LEDGER_MODULES, "system")}
    for module, amount in rows:
        by_module[str(module)] = int(amount or 0)

    transactions = db.scalars(
        select(PointTransaction)
        .where(PointTransaction.user_id == user.id)
        .order_by(PointTransaction.created_at.desc(), PointTransaction.id.desc())
        .limit(limit)
    ).all()
    traceable = sum(by_module[module] for module in POINT_LEDGER_MODULES)
    ledger_total = sum(by_module.values())
    return {
        "total": int(user.total_points or 0),
        "ledger_total": ledger_total,
        "traceable_points": traceable,
        "legacy_balance": by_module.get("system", 0),
        "by_module": by_module,
        "is_reconciled": ledger_total == int(user.total_points or 0),
        "recent_transactions": [
            {
                "id": row.id,
                "module": row.module,
                "module_label": MODULE_LABELS.get(row.module, row.module),
                "event_type": row.event_type,
                "source_id": row.source_id,
                "points": row.points,
                "description": row.description,
                "rule_version": row.rule_version,
                "created_at": row.created_at.isoformat(),
            }
            for row in transactions
        ],
    }
