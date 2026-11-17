"""数据模型聚合导出，便于 Alembic 自动发现全部表定义。"""
from app.database import Base
from app.models.community import (
    CommunityAttachment,
    CommunityContentReport,
    CommunityFavorite,
    CommunityLike,
    CommunityNotification,
    CommunityPost,
    CommunityPostView,
    CommunityReply,
    CommunityReplyLike,
    CommunityTopicFollow,
)
from app.models.debate import DebateMessage, DebatePracticeRecord, DebateTopic
from app.models.domain import (
    GeneratedReport,
    TaskRubricCriterion,
    TaskRubricScore,
    TaskSubmission,
    TeacherTask,
    TourRecord,
    TourSite,
)
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
from app.models.interview import InterviewMessage, InterviewPracticeRecord, InterviewScenario
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFavorite,
    KnowledgeIngestionJob,
    KnowledgeMessage,
    KnowledgeSession,
    KnowledgeTemplate,
    KnowledgeView,
)
from app.models.points import PointTransaction

# Import all models so Alembic can detect them
from app.models.user import User
