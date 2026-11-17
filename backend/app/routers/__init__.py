"""路由聚合导出：main.py 由此一次性注册全部业务模块。"""
from app.routers.ai_ops import router as ai_ops_router
from app.routers.auth import router as auth_router
from app.routers.community import router as community_router
from app.routers.debates import router as debates_router
from app.routers.history import router as history_router
from app.routers.immersive import router as immersive_router
from app.routers.interviews import router as interviews_router
from app.routers.knowledge import router as knowledge_router
from app.routers.media import router as tts_router
from app.routers.tours import router as tours_router
from app.routers.users import router as users_router
