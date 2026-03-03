from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Optional
from uuid import uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class StudentSubmission(SQLModel, table=True):
    __tablename__: ClassVar[str] = "student_submission"

    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    questionnaire_id: str = ""
    student_name: str = ""
    raw_answer: str = ""
    status: str = "pending"
    created_at: datetime | None = Field(default_factory=datetime.now)


class AIEvaluation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "ai_evaluation"

    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    submission_id: str = Field(default="", foreign_key="student_submission.id")
    student_self_reflection: str = ""
    teacher_scores: str = ""
    teacher_comment: str = ""
    raw_llm_output: str = ""
    reviewed_by_teacher: bool = False
    teacher_override: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class User(SQLModel, table=True):
    __tablename__: ClassVar[str] = "user"

    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    google_id: str = Field(default="", index=True, unique=True)
    email: str = ""
    name: str = ""
    avatar_url: str = ""
    role: str = "teacher"  # teacher / admin
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None


class LoginRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "login_record"

    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(default="", foreign_key="user.id")
    email: str = ""
    ip_address: str = ""
    user_agent: str = ""
    login_at: Optional[datetime] = Field(default_factory=datetime.now)


# --- Pydantic schemas (API responses) ---

class SubmissionCreate(BaseModel):
    questionnaire_id: str
    student_name: str
    answers: dict


class SubmissionResponse(BaseModel):
    id: str
    student_name: str
    questionnaire_id: str
    status: str
    answers: dict
    teacher_comment: str
    created_at: datetime


class TeacherReviewResponse(BaseModel):
    id: str
    student_name: str
    questionnaire_id: str
    status: str
    answers: dict
    teacher_comment: str
    teacher_override: Optional[str]
    student_self_reflection: dict
    teacher_scores: dict
    reviewed_by_teacher: bool
    created_at: datetime
