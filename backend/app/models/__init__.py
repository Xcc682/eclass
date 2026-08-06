from app.database import Base

# Import all models so Alembic can detect them
from app.models.user import User
from app.models.interview import InterviewScenario, InterviewPracticeRecord, InterviewMessage
from app.models.history import HistoryScenario, HistoryLearningRecord
from app.models.debate import DebateTopic, DebatePracticeRecord, DebateMessage
from app.models.community import (
    CommunityAttachment, CommunityContentReport, CommunityFavorite, CommunityLike,
    CommunityNotification, CommunityPost, CommunityPostView, CommunityReply,
    CommunityReplyLike, CommunityTopicFollow,
)
from app.models.knowledge import (
    KnowledgeChunk, KnowledgeDocument, KnowledgeFavorite, KnowledgeIngestionJob,
    KnowledgeMessage, KnowledgeSession, KnowledgeTemplate, KnowledgeView,
)
from app.models.domain import (
    TourSite, TourRecord, GeneratedReport, TaskRubricCriterion, TaskRubricScore,
    TaskSubmission, TeacherTask,
)
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
from app.models.points import PointTransaction
