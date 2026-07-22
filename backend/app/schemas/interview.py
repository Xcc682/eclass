from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class InterviewScenarioResponse(BaseModel):
    id: str; title: str; description: Optional[str] = ""
    difficulty: str = "intermediate"; estimated_duration: int = 15
    cover_image: Optional[str] = ""; ai_role_name: Optional[str] = ""
    ai_role_title: Optional[str] = ""
    class Config: from_attributes = True

class StartPracticeRequest(BaseModel):
    scenario_id: str

class StartPracticeResponse(BaseModel):
    id: str; first_question: str

class RespondRequest(BaseModel):
    content: str

class RespondResponse(BaseModel):
    question: str; analysis: Optional[Dict] = None
    is_completed: bool = False

class InterviewMessageResponse(BaseModel):
    id: str; role: str; content: str
    ai_analysis: Optional[Dict] = None; round_number: int
    created_at: datetime

class InterviewReportResponse(BaseModel):
    overall_score: int; grade: str
    dimension_scores: Dict[str, int]
    dimension_analysis: List[Dict]
    strengths: List[str]; weaknesses: List[str]
    suggestion: str; total_rounds: int
