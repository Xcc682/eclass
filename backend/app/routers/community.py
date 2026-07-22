from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.community import CommunityLike, CommunityPost, CommunityReply
from app.models.domain import TaskSubmission, TeacherTask
from app.models.user import User
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/v1/community", tags=["成长社区"])


class PostCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=2, max_length=10000)
    category: str = Field(default="学习心得", max_length=50)
    is_question: bool = False


class PostUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=2, max_length=10000)
    category: str = Field(default="学习心得", max_length=50)


class ReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=5000)
    deadline: str = Field(default="", max_length=30)


class SubmissionCreate(BaseModel):
    content: str = Field(min_length=2, max_length=10000)


class SubmissionReview(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str = Field(default="", max_length=5000)


def post_payload(db: Session, post: CommunityPost, author: User | None = None) -> dict:
    author = author or db.get(User, post.user_id)
    return {
        "id": post.id, "title": post.title, "content": post.content,
        "excerpt": post.content[:120], "category": post.category,
        "is_question": post.is_question, "resolved": post.resolved,
        "accepted_reply_id": post.accepted_reply_id,
        "author": author.nickname if author else "用户", "author_id": post.user_id,
        "likes": post.likes_count, "replies": post.replies_count,
        "views": post.view_count, "created_at": post.created_at.isoformat(),
    }


def owned_post(db: Session, post_id: str, user: User) -> CommunityPost:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "active":
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.user_id != user.id and user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="无权修改该帖子")
    return post


@router.get("/posts")
def list_posts(
    kind: str = Query(default="all", pattern=r"^(all|question|post)$"),
    q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    conditions = [CommunityPost.status == "active"]
    if kind == "question": conditions.append(CommunityPost.is_question.is_(True))
    elif kind == "post": conditions.append(CommunityPost.is_question.is_(False))
    if q.strip():
        term = f"%{q.strip()}%"
        conditions.append(or_(CommunityPost.title.ilike(term), CommunityPost.content.ilike(term)))
    total = int(db.scalar(select(func.count()).select_from(CommunityPost).where(*conditions)) or 0)
    rows = db.scalars(select(CommunityPost).where(*conditions).order_by(CommunityPost.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    user_ids = {row.user_id for row in rows}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
    return {"code": 0, "data": [post_payload(db, row, users.get(row.user_id)) for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.post("/posts")
def create_post(data: PostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = CommunityPost(user_id=user.id, **data.model_dump())
    db.add(post); db.flush()
    return {"code": 0, "data": post_payload(db, post), "message": "发布成功"}


@router.put("/posts/{post_id}")
def update_post(post_id: str, data: PostUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = owned_post(db, post_id, user)
    for key, value in data.model_dump().items(): setattr(post, key, value)
    return {"code": 0, "data": post_payload(db, post), "message": "修改成功"}


@router.delete("/posts/{post_id}")
def delete_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = owned_post(db, post_id, user); post.status = "deleted"
    return {"code": 0, "data": {"id": post.id, "deleted": True}}


@router.get("/posts/{post_id}")
def get_post(post_id: str, db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "active": raise HTTPException(status_code=404, detail="帖子不存在")
    post.view_count += 1
    replies = db.scalars(select(CommunityReply).where(CommunityReply.post_id == post.id).order_by(CommunityReply.created_at)).all()
    authors = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in replies}))).all()} if replies else {}
    data = post_payload(db, post)
    data["reply_list"] = [{
        "id": reply.id, "content": reply.content,
        "author": authors.get(reply.user_id).nickname if authors.get(reply.user_id) else "用户",
        "author_id": reply.user_id, "is_teacher": reply.is_teacher,
        "accepted": reply.id == post.accepted_reply_id,
        "likes": reply.likes_count, "created_at": reply.created_at.isoformat(),
    } for reply in replies]
    return {"code": 0, "data": data}


@router.post("/posts/{post_id}/replies")
def create_reply(post_id: str, data: ReplyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "active": raise HTTPException(status_code=404, detail="帖子不存在")
    reply = CommunityReply(post_id=post.id, user_id=user.id, content=data.content, is_teacher=user.role in {"teacher", "admin"})
    db.add(reply); db.flush(); post.replies_count += 1
    return {"code": 0, "data": {"id": reply.id, "content": reply.content, "author": user.nickname, "is_teacher": reply.is_teacher}}


@router.post("/posts/{post_id}/resolve/{reply_id}")
def resolve_question(post_id: str, reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = owned_post(db, post_id, user)
    if not post.is_question: raise HTTPException(status_code=409, detail="该帖子不是问答")
    reply = db.get(CommunityReply, reply_id)
    if not reply or reply.post_id != post.id: raise HTTPException(status_code=404, detail="回复不存在")
    post.resolved = True; post.accepted_reply_id = reply.id
    return {"code": 0, "data": {"resolved": True, "accepted_reply_id": reply.id}}


@router.post("/posts/{post_id}/like")
def like_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "active": raise HTTPException(status_code=404, detail="帖子不存在")
    existing = db.scalar(select(CommunityLike).where(CommunityLike.post_id == post.id, CommunityLike.user_id == user.id))
    if not existing:
        db.add(CommunityLike(post_id=post.id, user_id=user.id)); post.likes_count += 1
    return {"code": 0, "data": {"likes": post.likes_count, "liked": True}}


@router.delete("/posts/{post_id}/like")
def unlike_post(post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "active": raise HTTPException(status_code=404, detail="帖子不存在")
    existing = db.scalar(select(CommunityLike).where(CommunityLike.post_id == post.id, CommunityLike.user_id == user.id))
    if existing:
        db.delete(existing); post.likes_count = max(0, post.likes_count - 1)
    return {"code": 0, "data": {"likes": post.likes_count, "liked": False}}


@router.get("/tasks")
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TeacherTask).where(TeacherTask.status == "active").order_by(TeacherTask.created_at.desc())).all()
    submissions = {row.task_id: row for row in db.scalars(select(TaskSubmission).where(TaskSubmission.user_id == user.id)).all()}
    return {"code": 0, "data": [{
        "id": row.id, "title": row.title, "description": row.description, "deadline": row.deadline, "status": row.status,
        "submission": ({"id": submissions[row.id].id, "status": submissions[row.id].status, "score": submissions[row.id].score, "feedback": submissions[row.id].feedback} if row.id in submissions else None),
    } for row in rows]}


@router.post("/tasks")
def create_task(data: TaskCreate, user: User = Depends(require_role("teacher", "admin")), db: Session = Depends(get_db)):
    task = TeacherTask(creator_id=user.id, **data.model_dump()); db.add(task); db.flush()
    return {"code": 0, "data": {"id": task.id, **data.model_dump()}}


@router.post("/tasks/{task_id}/submissions")
def submit_task(task_id: str, data: SubmissionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(TeacherTask, task_id)
    if not task or task.status != "active": raise HTTPException(status_code=404, detail="任务不存在")
    submission = db.scalar(select(TaskSubmission).where(TaskSubmission.task_id == task_id, TaskSubmission.user_id == user.id))
    if submission and submission.status == "reviewed": raise HTTPException(status_code=409, detail="任务已批阅，不能再次修改")
    if submission:
        submission.content = data.content; submission.submitted_at = datetime.utcnow()
    else:
        submission = TaskSubmission(task_id=task_id, user_id=user.id, content=data.content); db.add(submission); db.flush()
    return {"code": 0, "data": {"id": submission.id, "status": submission.status}}


@router.get("/tasks/{task_id}/submissions")
def list_submissions(task_id: str, user: User = Depends(require_role("teacher", "admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(TaskSubmission).where(TaskSubmission.task_id == task_id).order_by(TaskSubmission.submitted_at.desc())).all()
    return {"code": 0, "data": [{"id": row.id, "user_id": row.user_id, "content": row.content, "status": row.status, "score": row.score, "feedback": row.feedback, "submitted_at": row.submitted_at.isoformat()} for row in rows]}


@router.put("/tasks/submissions/{submission_id}/review")
def review_submission(submission_id: str, data: SubmissionReview, user: User = Depends(require_role("teacher", "admin")), db: Session = Depends(get_db)):
    submission = db.get(TaskSubmission, submission_id)
    if not submission: raise HTTPException(status_code=404, detail="提交记录不存在")
    submission.score = data.score; submission.feedback = data.feedback; submission.status = "reviewed"; submission.reviewed_at = datetime.utcnow()
    return {"code": 0, "data": {"id": submission.id, "status": submission.status, "score": submission.score, "feedback": submission.feedback}}
