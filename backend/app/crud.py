from sqlalchemy.orm import Session
from .models import Job


def create_job(db: Session, job_data: dict):
    
    job = Job(**job_data)

    db.add(job)
    db.commit()
    db.refresh(job)

  
    return job


def get_jobs(db: Session):
    return db.query(Job).all()

