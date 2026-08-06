from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.community import (
    CommunityAttachment, CommunityContentReport, CommunityFavorite, CommunityLike,
    CommunityNotification, CommunityPost, CommunityPostView, CommunityReply,
    CommunityReplyLike, CommunityTopicFollow,
)
from app.models.domain import TaskRubricCriterion, TaskRubricScore, TaskSubmission, TeacherTask
from app.models.user import User
from app.security import get_current_user, get_optional_user, require_role
from app.services.community_storage import delete_file, read_file, save_bytes, storage_key
from app.services.point_service import award_points

router = APIRouter(prefix="/api/v1/community", tags=["成长社区"])
manager = require_role("teacher", "admin")
logger = logging.getLogger("app.community")
TOPICS = ("学习心得", "理论学习", "党史学习", "实践活动", "校园生活")
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
DOCUMENT_TYPES = {
    **IMAGE_TYPES,
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}


class PostCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=2, max_length=10000)
    category: str = Field(default="学习心得", max_length=50)
    is_question: bool = False
    attachment_ids: list[str] = Field(default_factory=list, max_length=3)
    submission_id: str | None = Field(default=None, min_length=8, max_length=64)


class PostUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=2, max_length=10000)
    category: str = Field(default="学习心得", max_length=50)
    attachment_ids: list[str] = Field(default_factory=list, max_length=3)


class ReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_reply_id: str | None = None
    submission_id: str | None = Field(default=None, min_length=8, max_length=64)


class ReportCreate(BaseModel):
    target_type: str = Field(pattern=r"^(post|reply)$")
    target_id: str
    reason: str = Field(min_length=2, max_length=50)
    detail: str = Field(default="", max_length=1000)


class ModerationAction(BaseModel):
    action: str = Field(pattern=r"^(hide|restore|dismiss)$")
    resolution: str = Field(default="", max_length=1000)


class RubricInput(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    weight: int = Field(ge=1, le=100)


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=5000)
    deadline: str = Field(default="", max_length=40)
    status: str = Field(default="published", pattern=r"^(draft|published)$")
    rubric: list[RubricInput] = Field(default_factory=lambda: [
        RubricInput(title="内容质量", description="内容完整、准确并回应任务要求", weight=60),
        RubricInput(title="思考深度", description="能够联系实际形成自己的理解", weight=40),
    ], min_length=2, max_length=5)
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def valid_rubric(self):
        if sum(item.weight for item in self.rubric) != 100:
            raise ValueError("评价量规权重合计必须为 100")
        return self


class TaskSubmissionSave(BaseModel):
    content: str = Field(default="", max_length=10000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)


class RubricScoreInput(BaseModel):
    criterion_id: str
    score: int = Field(ge=0, le=100)
    comment: str = Field(default="", max_length=1000)


class SubmissionReview(BaseModel):
    rubric_scores: list[RubricScoreInput] = Field(default_factory=list, max_length=5)
    score: int | None = Field(default=None, ge=0, le=100)
    feedback: str = Field(default="", max_length=5000)
    next_step: str = Field(default="", max_length=2000)


def _now() -> datetime:
    return datetime.utcnow()


def _parse_deadline(value: str) -> datetime | None:
    if not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="截止时间格式不正确") from exc
    if parsed.tzinfo:
        parsed = parsed.astimezone().replace(tzinfo=None)
    if len(raw) == 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


def _contains_sensitive_text(*values: str) -> bool:
    terms = [item.strip().lower() for item in settings.COMMUNITY_SENSITIVE_TERMS.split(",") if item.strip()]
    text = "\n".join(values).lower()
    return bool(terms and any(term in text for term in terms))


def _attachment_payload(item: CommunityAttachment) -> dict:
    return {
        "id": item.id, "name": item.original_name, "mime_type": item.mime_type,
        "size": item.size, "url": f"/api/v1/community/attachments/{item.id}",
    }


def _attachments(db: Session, target_type: str, target_id: str) -> list[dict]:
    rows = db.scalars(select(CommunityAttachment).where(
        CommunityAttachment.target_type == target_type,
        CommunityAttachment.target_id == target_id,
        CommunityAttachment.status == "attached",
    ).order_by(CommunityAttachment.created_at)).all()
    return [_attachment_payload(row) for row in rows]


def _bind_attachments(db: Session, user: User, ids: list[str], target_type: str, target_id: str) -> None:
    existing = db.scalars(select(CommunityAttachment).where(
        CommunityAttachment.target_type == target_type, CommunityAttachment.target_id == target_id,
    )).all()
    desired = set(ids)
    for item in existing:
        if item.id not in desired and item.owner_id == user.id:
            item.status, item.target_type, item.target_id = "temporary", None, None
            item.expires_at = _now() + timedelta(hours=24)
    if not ids:
        return
    rows = db.scalars(select(CommunityAttachment).where(CommunityAttachment.id.in_(ids))).all()
    if len(rows) != len(set(ids)) or any(row.owner_id != user.id for row in rows):
        raise HTTPException(status_code=403, detail="附件不存在或不属于当前用户")
    is_post = target_type == "post"
    if is_post and (len(rows) > 3 or any(row.mime_type not in IMAGE_TYPES or row.size > 5 * 1024 * 1024 for row in rows)):
        raise HTTPException(status_code=422, detail="帖子最多上传 3 张图片，每张不超过 5MB")
    if not is_post and (len(rows) > 5 or sum(row.size for row in rows) > 50 * 1024 * 1024):
        raise HTTPException(status_code=422, detail="任务附件最多 5 个，总计不超过 50MB")
    for row in rows:
        row.target_type, row.target_id, row.status, row.expires_at = target_type, target_id, "attached", None


def _notify(db: Session, *, user_id: str, actor_id: str | None, kind: str, title: str,
            content: str, resource_type: str, resource_id: str, event_key: str) -> None:
    if actor_id and actor_id == user_id:
        return
    if db.scalar(select(CommunityNotification.id).where(
        CommunityNotification.user_id == user_id, CommunityNotification.event_key == event_key,
    )):
        return
    db.add(CommunityNotification(
        user_id=user_id, actor_id=actor_id, type=kind, title=title, content=content[:500],
        resource_type=resource_type, resource_id=resource_id, event_key=event_key,
    ))


def _post_state(db: Session, post_id: str, user: User | None) -> tuple[bool, bool]:
    if not user:
        return False, False
    liked = db.scalar(select(CommunityLike.id).where(CommunityLike.user_id == user.id, CommunityLike.post_id == post_id)) is not None
    favorite = db.scalar(select(CommunityFavorite.id).where(CommunityFavorite.user_id == user.id, CommunityFavorite.post_id == post_id)) is not None
    return liked, favorite


def post_payload(db: Session, post: CommunityPost, user: User | None = None, author: User | None = None) -> dict:
    author = author or db.get(User, post.user_id)
    liked, favorited = _post_state(db, post.id, user)
    can_manage = bool(user and (user.id == post.user_id or user.role in {"teacher", "admin"}))
    return {
        "id": post.id, "title": post.title, "content": post.content,
        "excerpt": post.content[:160], "category": post.category,
        "is_question": post.is_question, "resolved": post.resolved,
        "accepted_reply_id": post.accepted_reply_id,
        "author": "社区管理员" if post.submission_id == "system-community-guide-v1" else (author.nickname if author else "用户"), "author_id": post.user_id,
        "avatar_url": author.avatar_url if author else "", "author_role": author.role if author else "student",
        "likes": post.likes_count, "replies": post.replies_count,
        "favorites": post.favorites_count, "views": post.view_count,
        "liked": liked, "favorited": favorited, "can_edit": can_manage,
        "pinned": post.pinned, "moderation_status": post.moderation_status,
        "attachments": _attachments(db, "post", post.id),
        "created_at": post.created_at.isoformat(), "updated_at": post.updated_at.isoformat(),
    }


def _reply_payload(db: Session, reply: CommunityReply, user: User | None, authors: dict[str, User]) -> dict:
    author = authors.get(reply.user_id)
    liked = bool(user and db.scalar(select(CommunityReplyLike.id).where(
        CommunityReplyLike.user_id == user.id, CommunityReplyLike.reply_id == reply.id,
    )))
    return {
        "id": reply.id, "content": reply.content,
        "author": author.nickname if author else "用户", "author_id": reply.user_id,
        "avatar_url": author.avatar_url if author else "", "author_role": author.role if author else "student",
        "is_teacher": reply.is_teacher, "parent_reply_id": reply.parent_reply_id,
        "likes": reply.likes_count, "liked": liked,
        "can_edit": bool(user and (user.id == reply.user_id or user.role in {"teacher", "admin"})),
        "created_at": reply.created_at.isoformat(), "updated_at": reply.updated_at.isoformat(),
    }


def _visible_post(db: Session, post_id: str, user: User | None = None) -> CommunityPost:
    post = db.get(CommunityPost, post_id)
    manager_view = bool(user and user.role in {"teacher", "admin"})
    owner_view = bool(user and post and post.user_id == user.id)
    if not post or post.status != "active" or (post.moderation_status != "published" and not (manager_view or owner_view)):
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


def _owned_post(db: Session, post_id: str, user: User) -> CommunityPost:
    post = _visible_post(db, post_id, user)
    if post.user_id != user.id and user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="无权修改该帖子")
    return post


def _ensure_community_guide(db: Session) -> None:
    visible_count = int(db.scalar(select(func.count()).select_from(CommunityPost).where(
        CommunityPost.status == "active", CommunityPost.moderation_status == "published",
    )) or 0)
    if visible_count:
        return
    author = db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)).order_by(User.created_at))
    if not author:
        return
    existing = db.scalar(select(CommunityPost).where(CommunityPost.submission_id == "system-community-guide-v1"))
    if existing:
        existing.status, existing.moderation_status = "active", "published"
        return
    db.add(CommunityPost(
        user_id=author.id,
        title="成长社区使用指南",
        content="这里用于分享真实学习收获、围绕资料提出问题，并在同伴互助与教师反馈中继续完善认识。发布时请写清背景与问题；引用资料时标明来源；讨论观点时尊重彼此。",
        category="社区指南",
        is_question=False,
        pinned=True,
        submission_id="system-community-guide-v1",
    ))
    db.flush()


def _task_status(task: TeacherTask) -> str:
    if task.status == "published" and task.deadline_at and task.deadline_at < _now():
        return "expired"
    return task.status


def _criteria(db: Session, task_id: str) -> list[TaskRubricCriterion]:
    rows = list(db.scalars(select(TaskRubricCriterion).where(
        TaskRubricCriterion.task_id == task_id,
    ).order_by(TaskRubricCriterion.sort_order)).all())
    if not rows:
        criterion = TaskRubricCriterion(task_id=task_id, title="完成质量", weight=100, sort_order=0)
        db.add(criterion); db.flush(); rows = [criterion]
    return rows


def _submission_payload(db: Session, item: TaskSubmission | None) -> dict | None:
    if not item:
        return None
    scores = db.scalars(select(TaskRubricScore).where(TaskRubricScore.submission_id == item.id)).all()
    return {
        "id": item.id, "content": item.content, "status": item.status, "score": item.score,
        "feedback": item.feedback, "next_step": item.next_step,
        "rubric_scores": [{"criterion_id": row.criterion_id, "score": row.score, "comment": row.comment} for row in scores],
        "attachments": _attachments(db, "submission", item.id),
        "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _task_payload(db: Session, task: TeacherTask, user: User) -> dict:
    submission = db.scalar(select(TaskSubmission).where(TaskSubmission.task_id == task.id, TaskSubmission.user_id == user.id))
    rubric = _criteria(db, task.id)
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "deadline": task.deadline, "deadline_at": task.deadline_at.isoformat() if task.deadline_at else None,
        "status": _task_status(task), "creator_id": task.creator_id,
        "can_manage": user.role in {"teacher", "admin"},
        "submission": _submission_payload(db, submission),
        "rubric": [{"id": row.id, "title": row.title, "description": row.description, "weight": row.weight} for row in rubric],
        "attachments": _attachments(db, "task", task.id),
        "created_at": task.created_at.isoformat(),
    }


@router.get("/feed")
def feed(
    section: str = Query(default="all", pattern=r"^(all|post|question)$"),
    sort_by: str = Query(default="latest", pattern=r"^(latest|hot|unanswered|followed)$"),
    topic: str = Query(default="", max_length=50), q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=15, ge=1, le=30),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _ensure_community_guide(db)
    conditions = [CommunityPost.status == "active", CommunityPost.moderation_status == "published"]
    if section == "post": conditions.append(CommunityPost.is_question.is_(False))
    if section == "question": conditions.append(CommunityPost.is_question.is_(True))
    if sort_by == "unanswered": conditions.extend([CommunityPost.is_question.is_(True), CommunityPost.resolved.is_(False)])
    if topic: conditions.append(CommunityPost.category == topic)
    if q.strip():
        term = f"%{q.strip()}%"; conditions.append(or_(CommunityPost.title.ilike(term), CommunityPost.content.ilike(term)))
    followed = list(db.scalars(select(CommunityTopicFollow.topic).where(CommunityTopicFollow.user_id == user.id)).all())
    if sort_by == "followed":
        if not followed:
            return {"code": 0, "data": {"items": [], "pagination": {"page": page, "page_size": page_size, "total": 0}, "followed_topics": []}}
        conditions.append(CommunityPost.category.in_(followed))
    order = [CommunityPost.pinned.desc()]
    if sort_by == "hot":
        order += [(CommunityPost.likes_count * 2 + CommunityPost.replies_count * 3 + CommunityPost.view_count / 20).desc(), CommunityPost.created_at.desc()]
    else:
        order += [CommunityPost.updated_at.desc()]
    total = int(db.scalar(select(func.count()).select_from(CommunityPost).where(*conditions)) or 0)
    rows = db.scalars(select(CommunityPost).where(*conditions).order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    unread = int(db.scalar(select(func.count()).select_from(CommunityNotification).where(
        CommunityNotification.user_id == user.id, CommunityNotification.is_read.is_(False),
    )) or 0)
    pending_tasks = int(db.scalar(select(func.count()).select_from(TeacherTask).where(TeacherTask.status == "published")) or 0)
    return {"code": 0, "data": {
        "items": [post_payload(db, row, user) for row in rows],
        "pagination": {"page": page, "page_size": page_size, "total": total},
        "followed_topics": followed, "topics": list(TOPICS),
        "summary": {"unread_notifications": unread, "active_tasks": pending_tasks},
    }}


@router.get("/posts")
def list_posts(kind: str = Query(default="all", pattern=r"^(all|question|post)$"), q: str = "", page: int = 1,
               page_size: int = 15, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    conditions = [CommunityPost.status == "active", CommunityPost.moderation_status == "published"]
    if kind == "question": conditions.append(CommunityPost.is_question.is_(True))
    elif kind == "post": conditions.append(CommunityPost.is_question.is_(False))
    if q.strip():
        term = f"%{q.strip()}%"; conditions.append(or_(CommunityPost.title.ilike(term), CommunityPost.content.ilike(term)))
    total = int(db.scalar(select(func.count()).select_from(CommunityPost).where(*conditions)) or 0)
    rows = db.scalars(select(CommunityPost).where(*conditions).order_by(CommunityPost.pinned.desc(), CommunityPost.created_at.desc()).offset((page - 1) * page_size).limit(min(page_size, 50))).all()
    return {"code": 0, "data": [post_payload(db, row, user) for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.post("/posts")
def create_post(data: PostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.submission_id:
        existing = db.scalar(select(CommunityPost).where(CommunityPost.user_id == user.id, CommunityPost.submission_id == data.submission_id))
        if existing: return {"code": 0, "data": post_payload(db, existing, user), "message": "发布成功"}
    moderation_status = "pending_review" if _contains_sensitive_text(data.title, data.content) else "published"
    post = CommunityPost(
        user_id=user.id, title=data.title.strip(), content=data.content.strip(), category=data.category,
        is_question=data.is_question, moderation_status=moderation_status, submission_id=data.submission_id,
    )
    db.add(post); db.flush(); _bind_attachments(db, user, data.attachment_ids, "post", post.id)
    followers = db.scalars(select(CommunityTopicFollow.user_id).where(CommunityTopicFollow.topic == post.category)).all()
    for follower_id in followers:
        _notify(db, user_id=follower_id, actor_id=user.id, kind="topic_post", title=f"{post.category}有新内容",
                content=post.title, resource_type="post", resource_id=post.id, event_key=f"topic-post:{post.id}")
    return {"code": 0, "data": post_payload(db, post, user), "message": "内容待审核" if moderation_status != "published" else "发布成功"}


@router.put("/posts/{post_id}")
def update_post(post_id: str, data: PostUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _owned_post(db, post_id, user)
    post.title, post.content, post.category = data.title.strip(), data.content.strip(), data.category
    if _contains_sensitive_text(post.title, post.content): post.moderation_status = "pending_review"
    _bind_attachments(db, user, data.attachment_ids, "post", post.id)
    return {"code": 0, "data": post_payload(db, post, user), "message": "修改成功"}


@router.delete("/posts/{post_id}")
def delete_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _owned_post(db, post_id, user); post.status = "deleted"
    return {"code": 0, "data": {"id": post.id, "deleted": True}}


@router.get("/posts/{post_id}")
def get_post(post_id: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user)
    if user:
        bucket = _now().strftime("%Y%m%d") + str(_now().hour // 6)
        if not db.scalar(select(CommunityPostView.id).where(
            CommunityPostView.user_id == user.id, CommunityPostView.post_id == post.id, CommunityPostView.view_bucket == bucket,
        )):
            db.add(CommunityPostView(user_id=user.id, post_id=post.id, view_bucket=bucket)); post.view_count += 1
    replies = list(db.scalars(select(CommunityReply).where(
        CommunityReply.post_id == post.id, CommunityReply.status == "active",
    ).order_by(CommunityReply.created_at)).all())
    author_ids = {row.user_id for row in replies} | {post.user_id}
    authors = {row.id: row for row in db.scalars(select(User).where(User.id.in_(author_ids))).all()}
    data = post_payload(db, post, user, authors.get(post.user_id))
    payloads = []
    for reply in replies:
        item = _reply_payload(db, reply, user, authors)
        item["accepted"] = reply.id == post.accepted_reply_id
        payloads.append(item)
    data["reply_list"] = sorted(payloads, key=lambda row: (not row["accepted"], row["created_at"]))
    return {"code": 0, "data": data}


@router.post("/posts/{post_id}/replies")
def create_reply(post_id: str, data: ReplyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user)
    if data.submission_id:
        existing = db.scalar(select(CommunityReply).where(
            CommunityReply.post_id == post.id, CommunityReply.user_id == user.id,
            CommunityReply.submission_id == data.submission_id,
        ))
        if existing:
            authors = {user.id: user}; return {"code": 0, "data": _reply_payload(db, existing, user, authors)}
    parent = db.get(CommunityReply, data.parent_reply_id) if data.parent_reply_id else None
    if parent and parent.post_id != post.id: raise HTTPException(status_code=422, detail="回复目标不属于当前帖子")
    reply = CommunityReply(
        post_id=post.id, user_id=user.id, content=data.content.strip(), parent_reply_id=parent.id if parent else None,
        is_teacher=user.role in {"teacher", "admin"}, submission_id=data.submission_id,
    )
    db.add(reply); db.flush(); post.replies_count += 1
    receiver = parent.user_id if parent else post.user_id
    _notify(db, user_id=receiver, actor_id=user.id, kind="reply", title=f"{user.nickname}回复了你",
            content=reply.content, resource_type="post", resource_id=post.id, event_key=f"reply:{reply.id}")
    return {"code": 0, "data": _reply_payload(db, reply, user, {user.id: user})}


@router.delete("/replies/{reply_id}")
def delete_reply(reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reply = db.get(CommunityReply, reply_id)
    if not reply or reply.status != "active": raise HTTPException(status_code=404, detail="回复不存在")
    if reply.user_id != user.id and user.role not in {"teacher", "admin"}: raise HTTPException(status_code=403, detail="无权删除该回复")
    reply.status = "deleted"; post = db.get(CommunityPost, reply.post_id)
    if post: post.replies_count = max(0, post.replies_count - 1)
    return {"code": 0, "data": {"deleted": True}}


@router.post("/posts/{post_id}/resolve/{reply_id}")
def resolve_question(post_id: str, reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _owned_post(db, post_id, user)
    if not post.is_question: raise HTTPException(status_code=409, detail="该帖子不是问答")
    if post.resolved:
        if post.accepted_reply_id == reply_id:
            return {"code": 0, "data": {"resolved": True, "accepted_reply_id": reply_id, "points_awarded": 0}}
        raise HTTPException(status_code=409, detail="问题已经采纳其他回答")
    reply = db.get(CommunityReply, reply_id)
    if not reply or reply.post_id != post.id or reply.status != "active": raise HTTPException(status_code=404, detail="回复不存在")
    post.resolved, post.accepted_reply_id = True, reply.id
    awarded = False
    answerer = db.get(User, reply.user_id)
    if answerer and answerer.id != post.user_id:
        _, awarded = award_points(db, answerer, module="community", event_type="accepted_answer",
                                  source_id=reply.id, points=2, description="互助问答被采纳")
    _notify(db, user_id=reply.user_id, actor_id=user.id, kind="accepted", title="你的回答被采纳",
            content=post.title, resource_type="post", resource_id=post.id, event_key=f"accepted:{reply.id}")
    return {"code": 0, "data": {"resolved": True, "accepted_reply_id": reply.id, "points_awarded": 2 if awarded else 0}}


def _toggle_post_relation(db: Session, model, post: CommunityPost, user: User, enabled: bool, count_field: str) -> dict:
    existing = db.scalar(select(model).where(model.post_id == post.id, model.user_id == user.id))
    if enabled and not existing:
        db.add(model(post_id=post.id, user_id=user.id)); setattr(post, count_field, getattr(post, count_field) + 1)
    elif not enabled and existing:
        db.delete(existing); setattr(post, count_field, max(0, getattr(post, count_field) - 1))
    return {"enabled": enabled, "count": getattr(post, count_field)}


@router.post("/posts/{post_id}/like")
def like_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user); value = _toggle_post_relation(db, CommunityLike, post, user, True, "likes_count")
    return {"code": 0, "data": {"likes": value["count"], "liked": True}}


@router.delete("/posts/{post_id}/like")
def unlike_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user); value = _toggle_post_relation(db, CommunityLike, post, user, False, "likes_count")
    return {"code": 0, "data": {"likes": value["count"], "liked": False}}


@router.post("/posts/{post_id}/favorite")
def favorite_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user); value = _toggle_post_relation(db, CommunityFavorite, post, user, True, "favorites_count")
    return {"code": 0, "data": {"favorites": value["count"], "favorited": True}}


@router.delete("/posts/{post_id}/favorite")
def unfavorite_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _visible_post(db, post_id, user); value = _toggle_post_relation(db, CommunityFavorite, post, user, False, "favorites_count")
    return {"code": 0, "data": {"favorites": value["count"], "favorited": False}}


@router.post("/replies/{reply_id}/like")
def like_reply(reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reply = db.get(CommunityReply, reply_id)
    if not reply or reply.status != "active": raise HTTPException(status_code=404, detail="回复不存在")
    existing = db.scalar(select(CommunityReplyLike).where(CommunityReplyLike.reply_id == reply.id, CommunityReplyLike.user_id == user.id))
    if not existing: db.add(CommunityReplyLike(reply_id=reply.id, user_id=user.id)); reply.likes_count += 1
    return {"code": 0, "data": {"likes": reply.likes_count, "liked": True}}


@router.delete("/replies/{reply_id}/like")
def unlike_reply(reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reply = db.get(CommunityReply, reply_id)
    if not reply: raise HTTPException(status_code=404, detail="回复不存在")
    existing = db.scalar(select(CommunityReplyLike).where(CommunityReplyLike.reply_id == reply.id, CommunityReplyLike.user_id == user.id))
    if existing: db.delete(existing); reply.likes_count = max(0, reply.likes_count - 1)
    return {"code": 0, "data": {"likes": reply.likes_count, "liked": False}}


@router.get("/topics")
def topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    followed = set(db.scalars(select(CommunityTopicFollow.topic).where(CommunityTopicFollow.user_id == user.id)).all())
    counts = dict(db.execute(select(CommunityPost.category, func.count()).where(
        CommunityPost.status == "active", CommunityPost.moderation_status == "published",
    ).group_by(CommunityPost.category)).all())
    return {"code": 0, "data": [{"name": topic, "followed": topic in followed, "posts": counts.get(topic, 0)} for topic in TOPICS]}


@router.post("/topics/{topic}/follow")
def follow_topic(topic: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if topic not in TOPICS: raise HTTPException(status_code=404, detail="分类不存在")
    if not db.scalar(select(CommunityTopicFollow.id).where(CommunityTopicFollow.user_id == user.id, CommunityTopicFollow.topic == topic)):
        db.add(CommunityTopicFollow(user_id=user.id, topic=topic))
    return {"code": 0, "data": {"topic": topic, "followed": True}}


@router.delete("/topics/{topic}/follow")
def unfollow_topic(topic: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(CommunityTopicFollow).where(CommunityTopicFollow.user_id == user.id, CommunityTopicFollow.topic == topic))
    if row: db.delete(row)
    return {"code": 0, "data": {"topic": topic, "followed": False}}


@router.get("/notifications")
def notifications(page: int = 1, page_size: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = int(db.scalar(select(func.count()).select_from(CommunityNotification).where(CommunityNotification.user_id == user.id)) or 0)
    rows = db.scalars(select(CommunityNotification).where(CommunityNotification.user_id == user.id).order_by(
        CommunityNotification.created_at.desc()).offset((page - 1) * page_size).limit(min(page_size, 50))).all()
    unread = int(db.scalar(select(func.count()).select_from(CommunityNotification).where(
        CommunityNotification.user_id == user.id, CommunityNotification.is_read.is_(False))) or 0)
    return {"code": 0, "data": {"items": [{
        "id": row.id, "type": row.type, "title": row.title, "content": row.content,
        "resource_type": row.resource_type, "resource_id": row.resource_id, "is_read": row.is_read,
        "created_at": row.created_at.isoformat(),
    } for row in rows], "unread": unread, "pagination": {"page": page, "page_size": page_size, "total": total}}}


@router.post("/notifications/read-all")
def read_all_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(CommunityNotification).where(CommunityNotification.user_id == user.id, CommunityNotification.is_read.is_(False))).all()
    for row in rows: row.is_read = True
    return {"code": 0, "data": {"updated": len(rows)}}


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CommunityNotification, notification_id)
    if not row or row.user_id != user.id: raise HTTPException(status_code=404, detail="消息不存在")
    row.is_read = True
    return {"code": 0, "data": {"id": row.id, "is_read": True}}


@router.get("/me")
def my_community(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = db.scalars(select(CommunityPost).where(CommunityPost.user_id == user.id, CommunityPost.status == "active").order_by(CommunityPost.updated_at.desc())).all()
    favorites = db.scalars(select(CommunityPost).join(CommunityFavorite, CommunityFavorite.post_id == CommunityPost.id).where(
        CommunityFavorite.user_id == user.id, CommunityPost.status == "active", CommunityPost.moderation_status == "published",
    ).order_by(CommunityFavorite.created_at.desc())).all()
    reply_post_ids = list(db.scalars(select(CommunityReply.post_id).where(CommunityReply.user_id == user.id, CommunityReply.status == "active").distinct()).all())
    replied = db.scalars(select(CommunityPost).where(CommunityPost.id.in_(reply_post_ids))).all() if reply_post_ids else []
    followed = list(db.scalars(select(CommunityTopicFollow.topic).where(CommunityTopicFollow.user_id == user.id)).all())
    return {"code": 0, "data": {
        "posts": [post_payload(db, row, user) for row in posts],
        "favorites": [post_payload(db, row, user) for row in favorites],
        "replied": [post_payload(db, row, user) for row in replied], "followed_topics": followed,
    }}


@router.post("/reports")
def report_content(data: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(CommunityPost if data.target_type == "post" else CommunityReply, data.target_id)
    if not target: raise HTTPException(status_code=404, detail="举报内容不存在")
    existing = db.scalar(select(CommunityContentReport).where(
        CommunityContentReport.reporter_id == user.id, CommunityContentReport.target_type == data.target_type,
        CommunityContentReport.target_id == data.target_id,
    ))
    if not existing: db.add(CommunityContentReport(reporter_id=user.id, **data.model_dump()))
    return {"code": 0, "data": {"reported": True}}


@router.get("/moderation/reports")
def moderation_reports(status_filter: str = "pending", _: User = Depends(manager), db: Session = Depends(get_db)):
    rows = db.scalars(select(CommunityContentReport).where(CommunityContentReport.status == status_filter).order_by(CommunityContentReport.created_at.desc())).all()
    return {"code": 0, "data": [{"id": row.id, "target_type": row.target_type, "target_id": row.target_id,
        "reason": row.reason, "detail": row.detail, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]}


@router.put("/moderation/reports/{report_id}")
def moderate_report(report_id: str, data: ModerationAction, user: User = Depends(manager), db: Session = Depends(get_db)):
    row = db.get(CommunityContentReport, report_id)
    if not row: raise HTTPException(status_code=404, detail="举报不存在")
    target = db.get(CommunityPost if row.target_type == "post" else CommunityReply, row.target_id)
    if target and data.action == "hide":
        if row.target_type == "post": target.moderation_status = "hidden"
        else: target.status = "hidden"
    elif target and data.action == "restore":
        if row.target_type == "post": target.moderation_status = "published"
        else: target.status = "active"
    row.status = "dismissed" if data.action == "dismiss" else "resolved"
    row.reviewer_id, row.resolution, row.reviewed_at = user.id, data.resolution, _now()
    return {"code": 0, "data": {"id": row.id, "status": row.status}}


@router.post("/attachments/upload", status_code=status.HTTP_201_CREATED)
async def upload_attachment(purpose: str = Form(default="task"), file: UploadFile = File(...),
                            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expired = db.scalars(select(CommunityAttachment).where(
        CommunityAttachment.status == "temporary", CommunityAttachment.expires_at < _now(),
    ).limit(30)).all()
    for item in expired:
        try: delete_file(item.storage_key, item.storage_backend)
        except Exception as exc:
            logger.warning("[community] expired attachment cleanup failed key=%s error=%s: %s", item.storage_key, exc.__class__.__name__, exc)
        db.delete(item)
    allowed = IMAGE_TYPES if purpose == "post_image" else DOCUMENT_TYPES
    mime = (file.content_type or "").lower()
    if mime not in allowed: raise HTTPException(status_code=415, detail="不支持的附件格式")
    limit = 5 * 1024 * 1024 if purpose == "post_image" else 20 * 1024 * 1024
    content = await file.read(limit + 1)
    if len(content) > limit: raise HTTPException(status_code=413, detail=f"文件不能超过 {limit // 1024 // 1024}MB")
    if mime in IMAGE_TYPES:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(content)) as image: image.verify()
        except Exception as exc:
            raise HTTPException(status_code=415, detail="图片内容损坏或格式不正确") from exc
    suffix = allowed[mime]; key = storage_key(suffix); backend = save_bytes(key, content, mime)
    item = CommunityAttachment(
        owner_id=user.id, original_name=Path(file.filename or f"upload{suffix}").name,
        storage_key=key, storage_backend=backend, mime_type=mime, size=len(content), expires_at=_now() + timedelta(hours=24),
    )
    db.add(item); db.flush()
    return {"code": 0, "data": _attachment_payload(item)}


@router.get("/attachments/{attachment_id}")
def download_attachment(attachment_id: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    item = db.get(CommunityAttachment, attachment_id)
    if not item: raise HTTPException(status_code=404, detail="附件不存在")
    public_post_image = False
    if item.target_type == "post" and item.status == "attached" and item.mime_type in IMAGE_TYPES:
        post = db.get(CommunityPost, item.target_id)
        public_post_image = bool(post and post.status == "active" and post.moderation_status == "published")
    if not public_post_image:
        if not user:
            raise HTTPException(status_code=401, detail="无权访问该附件")
        allowed = (
            item.owner_id == user.id
            or user.role in {"teacher", "admin"}
        )
        if not allowed and item.target_type == "task":
            # Task materials are shared with every student once published.
            task = db.get(TeacherTask, item.target_id)
            allowed = bool(task and task.status in {"published", "closed"})
        if not allowed and item.target_type == "submission":
            # A student may only view attachments of their own submission.
            submission = db.get(TaskSubmission, item.target_id)
            allowed = bool(submission and submission.user_id == user.id)
        if not allowed:
            raise HTTPException(status_code=403, detail="无权访问该附件")
    try: source, _ = read_file(item.storage_key, item.storage_backend)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail="附件文件不存在") from exc
    if isinstance(source, Path): return FileResponse(source, filename=item.original_name, media_type=item.mime_type)
    return StreamingResponse(source, media_type=item.mime_type, headers={"Content-Disposition": f'inline; filename="{item.original_name}"'})


@router.delete("/attachments/{attachment_id}")
def remove_attachment(attachment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CommunityAttachment, attachment_id)
    if not item or (item.owner_id != user.id and user.role not in {"teacher", "admin"}): raise HTTPException(status_code=404, detail="附件不存在")
    delete_file(item.storage_key, item.storage_backend); db.delete(item)
    return {"code": 0, "data": {"deleted": True}}


@router.get("/tasks")
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(TeacherTask)
    if user.role not in {"teacher", "admin"}: query = query.where(TeacherTask.status == "published")
    rows = db.scalars(query.order_by(TeacherTask.created_at.desc())).all()
    return {"code": 0, "data": [_task_payload(db, row, user) for row in rows]}


@router.post("/tasks")
def create_task(data: TaskCreate, user: User = Depends(manager), db: Session = Depends(get_db)):
    task = TeacherTask(creator_id=user.id, title=data.title.strip(), description=data.description.strip(),
                       deadline=data.deadline, deadline_at=_parse_deadline(data.deadline), status=data.status)
    db.add(task); db.flush()
    for index, item in enumerate(data.rubric): db.add(TaskRubricCriterion(task_id=task.id, sort_order=index, **item.model_dump()))
    db.flush()
    _bind_attachments(db, user, data.attachment_ids, "task", task.id)
    if task.status == "published":
        students = db.scalars(select(User.id).where(User.is_active.is_(True), User.role == "student")).all()
        for student_id in students:
            _notify(db, user_id=student_id, actor_id=user.id, kind="task_published", title="新的教师任务",
                    content=task.title, resource_type="task", resource_id=task.id, event_key=f"task-published:{task.id}")
    return {"code": 0, "data": _task_payload(db, task, user)}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task or (task.status == "draft" and user.role not in {"teacher", "admin"}): raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "data": _task_payload(db, task, user)}


@router.put("/tasks/{task_id}")
def update_task(task_id: str, data: TaskCreate, user: User = Depends(manager), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    existing_criteria = _criteria(db, task.id)
    reviewed_count = int(db.scalar(select(func.count()).select_from(TaskSubmission).where(
        TaskSubmission.task_id == task.id, TaskSubmission.status == "reviewed",
    )) or 0)
    current_rubric = [(row.title, row.description or "", row.weight) for row in existing_criteria]
    requested_rubric = [(row.title, row.description or "", row.weight) for row in data.rubric]
    if reviewed_count and current_rubric != requested_rubric:
        raise HTTPException(status_code=409, detail="已有批阅结果，不能修改评价量规；可以修改任务说明或关闭后新建任务")
    task.title, task.description, task.deadline = data.title.strip(), data.description.strip(), data.deadline
    task.deadline_at, task.status = _parse_deadline(data.deadline), data.status
    if not reviewed_count:
        db.execute(delete(TaskRubricCriterion).where(TaskRubricCriterion.task_id == task.id))
        for index, item in enumerate(data.rubric):
            db.add(TaskRubricCriterion(task_id=task.id, sort_order=index, **item.model_dump()))
        db.flush()
    _bind_attachments(db, user, data.attachment_ids, "task", task.id)
    return {"code": 0, "data": _task_payload(db, task, user)}


@router.post("/tasks/{task_id}/publish")
def publish_task(task_id: str, user: User = Depends(manager), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "published"
    students = db.scalars(select(User.id).where(User.is_active.is_(True), User.role == "student")).all()
    for student_id in students:
        _notify(db, user_id=student_id, actor_id=user.id, kind="task_published", title="新的教师任务",
                content=task.title, resource_type="task", resource_id=task.id, event_key=f"task-published:{task.id}")
    return {"code": 0, "data": {"id": task.id, "status": task.status}}


@router.post("/tasks/{task_id}/close")
def close_task(task_id: str, _: User = Depends(manager), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "closed"; return {"code": 0, "data": {"id": task.id, "status": task.status}}


def _save_submission(task: TeacherTask, data: TaskSubmissionSave, user: User, db: Session, submit: bool) -> TaskSubmission:
    if _task_status(task) != "published": raise HTTPException(status_code=409, detail="任务已截止或关闭")
    item = db.scalar(select(TaskSubmission).where(TaskSubmission.task_id == task.id, TaskSubmission.user_id == user.id))
    if item and item.status == "reviewed": raise HTTPException(status_code=409, detail="任务已批阅，不能再次修改")
    if submit and len(data.content.strip()) < 2 and not data.attachment_ids: raise HTTPException(status_code=422, detail="请填写学习成果或上传附件")
    if not item:
        item = TaskSubmission(task_id=task.id, user_id=user.id, content=data.content.strip(), status="draft")
        db.add(item); db.flush()
    item.content, item.updated_at = data.content.strip(), _now()
    if submit: item.status, item.submitted_at = "submitted", _now()
    _bind_attachments(db, user, data.attachment_ids, "submission", item.id)
    return item


@router.patch("/tasks/{task_id}/submission")
def save_submission_draft(task_id: str, data: TaskSubmissionSave, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    item = _save_submission(task, data, user, db, False)
    return {"code": 0, "data": _submission_payload(db, item)}


@router.post("/tasks/{task_id}/submission/submit")
def submit_task_v2(task_id: str, data: TaskSubmissionSave, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    item = _save_submission(task, data, user, db, True)
    return {"code": 0, "data": _submission_payload(db, item)}


@router.post("/tasks/{task_id}/submissions")
def submit_task_compat(task_id: str, data: TaskSubmissionSave, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return submit_task_v2(task_id, data, user, db)


@router.get("/tasks/{task_id}/submissions")
def list_submissions(task_id: str, status_filter: str = "", _: User = Depends(manager), db: Session = Depends(get_db)):
    query = select(TaskSubmission).where(TaskSubmission.task_id == task_id)
    if status_filter: query = query.where(TaskSubmission.status == status_filter)
    rows = db.scalars(query.order_by(TaskSubmission.updated_at.desc())).all()
    users = {row.id: row for row in db.scalars(select(User).where(User.id.in_({item.user_id for item in rows}))).all()} if rows else {}
    return {"code": 0, "data": [{**(_submission_payload(db, row) or {}), "user_id": row.user_id,
        "user_name": users.get(row.user_id).nickname if users.get(row.user_id) else "学生"} for row in rows]}


@router.put("/tasks/submissions/{submission_id}/review")
def review_submission(submission_id: str, data: SubmissionReview, user: User = Depends(manager), db: Session = Depends(get_db)):
    submission = db.get(TaskSubmission, submission_id)
    if not submission: raise HTTPException(status_code=404, detail="提交记录不存在")
    criteria = _criteria(db, submission.task_id); by_id = {row.id: row for row in criteria}
    provided_scores = data.rubric_scores
    if not provided_scores and data.score is not None:
        provided_scores = [RubricScoreInput(criterion_id=row.id, score=data.score) for row in criteria]
    scores = {row.criterion_id: row for row in provided_scores}
    if set(scores) != set(by_id): raise HTTPException(status_code=422, detail="请完成全部评价维度")
    db.execute(delete(TaskRubricScore).where(TaskRubricScore.submission_id == submission.id))
    total = 0.0
    for criterion in criteria:
        value = scores[criterion.id]; total += value.score * criterion.weight / 100
        db.add(TaskRubricScore(submission_id=submission.id, criterion_id=criterion.id, score=value.score, comment=value.comment))
    submission.score, submission.feedback, submission.next_step = round(total), data.feedback, data.next_step
    submission.status, submission.reviewed_at = "reviewed", _now()
    student = db.get(User, submission.user_id); awarded = False
    if student and submission.score >= 60:
        _, awarded = award_points(db, student, module="community", event_type="task_passed", source_id=submission.id,
                                  points=3, description="教师任务通过评阅")
    _notify(db, user_id=submission.user_id, actor_id=user.id, kind="task_reviewed", title="教师任务已批阅",
            content=f"得分 {submission.score}", resource_type="task", resource_id=submission.task_id,
            event_key=f"task-reviewed:{submission.id}")
    return {"code": 0, "data": {**(_submission_payload(db, submission) or {}), "points_awarded": 3 if awarded else 0}}
