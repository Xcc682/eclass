"""Assign a content-management role by phone number."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a user's role")
    parser.add_argument("phone")
    parser.add_argument("role", choices=["student", "teacher", "admin"])
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == args.phone))
        if not user:
            raise SystemExit("用户不存在，请先使用该手机号登录一次")
        user.role = args.role
        db.commit()
        print(f"已将 {args.phone} 设置为 {args.role}")


if __name__ == "__main__":
    main()
