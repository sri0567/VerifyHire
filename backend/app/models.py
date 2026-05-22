from sqlalchemy import Column, Integer, String, Boolean, Text
from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    salary = Column(String)
    source = Column(String)
    description = Column(Text)

    legitimacy_score = Column(Integer)
    legitimacy_reason = Column(Text)
    ai_analysis_raw = Column(Text, nullable=True) 
    verified_remote = Column(Boolean, default=False)
    scam_flag = Column(Boolean, default=False)
    apply_url = Column(String, nullable=True)
    source_job_id = Column(String, unique=True, nullable=True, index=True)