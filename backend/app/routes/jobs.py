import json
from collections import Counter

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..agents import build_agent_report
from ..ai import analyze_job_with_ai
from ..crud import create_job
from ..database import get_db
from ..models import Job
from ..schemas import JobCreate, JobResponse
from ..scrapers import fetch_remoteok_jobs,fetch_all_remoteok_jobs
from ..verifier import (
    calculate_score,
    check_remote_validity,
    clean_description,
    detect_scam_phrases,
    extract_summary,
)

router = APIRouter()


def _serialize_ai_payload(agent_report: dict, llm_summary: str | None) -> str:
    payload = {"agent_report": agent_report, "llm_summary": llm_summary}
    return json.dumps(payload, ensure_ascii=False)


def _build_consensus_score(description: str, agent_score: int, verified_remote: bool) -> int:
    phrase_flags = detect_scam_phrases(description)
    heuristic_score = calculate_score(phrase_flags, verified_remote)
    return int(round((agent_score + heuristic_score) / 2))


@router.get("/")
def all_jobs(
    db: Session = Depends(get_db),
    query: str | None = Query(default=None, description="Search by title/company/description"),
    min_score: int = Query(default=0, ge=0, le=100),
    remote_only: bool = Query(default=False),
    max_results: int = Query(default=200, ge=1, le=500),
):
    db_query = db.query(Job)

    if query:
        like_value = f"%{query}%"
        db_query = db_query.filter(
            or_(
                Job.title.ilike(like_value),
                Job.company.ilike(like_value),
                Job.description.ilike(like_value),
            )
        )

    if min_score:
        db_query = db_query.filter(Job.legitimacy_score >= min_score)

    if remote_only:
        db_query = db_query.filter(Job.verified_remote.is_(True))

    jobs = db_query.order_by(Job.id.desc()).limit(max_results).all()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/insights")
def get_job_insights(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    if not jobs:
        return {
            "total_jobs": 0,
            "high_confidence_jobs": 0,
            "verified_remote_jobs": 0,
            "potentially_risky_jobs": 0,
            "average_score": 0,
            "top_sources": [],
        }

    total = len(jobs)
    high_confidence = len([job for job in jobs if job.legitimacy_score >= 80 and not job.scam_flag])
    verified_remote = len([job for job in jobs if job.verified_remote])
    risky = len([job for job in jobs if job.legitimacy_score < 60 or job.scam_flag])
    avg_score = round(sum(job.legitimacy_score or 0 for job in jobs) / total, 1)
    source_counts = Counter([(job.source or "Unknown") for job in jobs])

    return {
        "total_jobs": total,
        "high_confidence_jobs": high_confidence,
        "verified_remote_jobs": verified_remote,
        "potentially_risky_jobs": risky,
        "average_score": avg_score,
        "top_sources": [
            {"source": source, "count": count}
            for source, count in source_counts.most_common(5)
        ],
    }


@router.post("/", response_model=JobResponse)
def create_new_job(job: JobCreate, db: Session = Depends(get_db)):
    description = clean_description(job.description, max_length=2000)
    verified_remote = check_remote_validity(description)

    agent_report = build_agent_report(
        title=job.title,
        company=job.company,
        description=description,
        location=job.location,
        salary=job.salary,
        apply_url=None,
    )
    consensus_score = _build_consensus_score(description, agent_report["score"], verified_remote)
    llm_summary = analyze_job_with_ai(description)
    phrase_flags = detect_scam_phrases(description)

    job_data = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "source": job.source or "Manual",
        "description": extract_summary(description, max_length=350),
        "legitimacy_score": consensus_score,
        "legitimacy_reason": agent_report["summary"],
        "verified_remote": verified_remote,
        "scam_flag": len(phrase_flags) > 0 or agent_report["risk_level"] == "high",
        "ai_analysis_raw": _serialize_ai_payload(agent_report, llm_summary),
    }

    created_job = create_job(db, job_data)
    return created_job


@router.post("/scrape")
async def run_scraper_in_background():
    """Runs job scraping and multi-agent verification."""
    from ..database import SessionLocal

    db = SessionLocal()

    try:
        print("Background scraper started...")

        jobs = await fetch_all_remoteok_jobs(db,batch_size=10,max_batches=5)
        saved_count = 0
        error_count = 0
        duplicate_count = 0

        for api_job in jobs:
            try:
                remote_ok_id = str(api_job.get("id"))
                title = api_job.get("title", "") or "Untitled Position"
                company = api_job.get("company_board", "Unknown Company")

                raw_description = api_job.get("content") or api_job.get("description") or ""
                description = clean_description(raw_description, max_length=1500)
                

                if not description or len(description) < 50:
                    print(f"No valid description for {title}, skipping...")
                    continue

                location = api_job.get("location", {})
                if isinstance(location, dict):
                    location = location.get("name", "Remote")
                elif not location:
                    location = "Remote"

                apply_url = api_job.get("absolute_url", "")
                if not apply_url:
                    job_id = api_job.get("id")
                    if job_id and company:
                        apply_url = f"https://remoteok.com/jobs/{job_id}"
                    else:
                        apply_url = "#"

                existing = db.query(Job).filter(Job.source_job_id == remote_ok_id).first()
                if existing:
                    duplicate_count += 1
                    continue

                verified_remote = check_remote_validity(description)
                agent_report = build_agent_report(
                    title=title,
                    company=company,
                    description=description,
                    location=location,
                    salary="Not specified",
                    apply_url=apply_url,
                )
                consensus_score = _build_consensus_score(description, agent_report["score"], verified_remote)
                llm_summary = analyze_job_with_ai(description)
                phrase_flags = detect_scam_phrases(description)

                job_data = {
                    "title": title[:255],
                    "company": company[:255],
                    "location": (location or "Remote")[:255],
                    "salary": "Not specified",
                    "source": "RemoteOk",
                    "description": description,
                    "legitimacy_score": consensus_score,
                    "legitimacy_reason": agent_report["summary"],
                    "verified_remote": verified_remote,
                    "ai_analysis_raw": _serialize_ai_payload(agent_report, llm_summary),
                    "scam_flag": len(phrase_flags) > 0 or agent_report["risk_level"] == "high",
                    "apply_url": apply_url,
                    "source_job_id": remote_ok_id,
                }

                create_job(db, job_data)
                saved_count += 1

                if saved_count <= 5:
                    print(f"Saved: {title} | score={consensus_score}")
            except Exception as exc:
                error_count += 1
                print(f"Error while processing job: {exc}")
                continue

        summary = {
            "saved_count": saved_count,
            "error_count": error_count,
            "duplicate_count": duplicate_count,
            "fetched_count": len(jobs),
        }
        print(f"Scraper summary: {summary}")
        return summary
    finally:
        db.close()


@router.post("/scrape/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Start scraper in background."""
    background_tasks.add_task(run_scraper_in_background)
    return {"message": "Scraping started in background"}