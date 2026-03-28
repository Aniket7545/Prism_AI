from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class ContentRequest(BaseModel):
    id: str
    topic: str
    target_audience: str
    channel: str  # e.g., LinkedIn, Blog, Email
    raw_input: str
    region: str = "Global"

class ComplianceReport(BaseModel):
    status: ComplianceStatus
    risk_score: float  # 0.0 to 1.0
    flags: List[str]
    reasoning: str

class ContentDraft(BaseModel):
    id: str
    content: str
    version: int
    created_at: datetime = Field(default_factory=datetime.now)

class AuditLog(BaseModel):
    timestamp: datetime
    agent_name: str
    action: str
    input_summary: str
    output_summary: str
    status: str