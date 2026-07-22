from app.database import Base

# Import all models so Alembic can detect them
from app.models.user import User
from app.models.interview import InterviewScenario, InterviewPracticeRecord, InterviewMessage
from app.models.history import HistoryScenario, HistoryLearningRecord
from app.models.debate import DebateTopic, DebatePracticeRecord, DebateMessage
from app.models.community import CommunityLike, CommunityPost, CommunityReply
from app.models.knowledge import (
    KnowledgeChunk, KnowledgeDocument, KnowledgeFavorite, KnowledgeIngestionJob,
    KnowledgeMessage, KnowledgeSession, KnowledgeTemplate, KnowledgeView,
)
from app.models.domain import TourSite, TourRecord, GeneratedReport, TaskSubmission, TeacherTask
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
