from pydantic import BaseModel
from typing import Optional


class JobCreate(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    salary: Optional[str] = None
    source: Optional[str] = None
    description: str


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    salary: str | None
    source: str | None
    description: str
    legitimacy_score: int
    legitimacy_reason: str
    verified_remote: bool
    scam_flag: bool
    ai_analysis_raw: str | None = None
    apply_url:str| None = None
    source_job_id:str | None = None

    class Config:
        from_attributes = True
