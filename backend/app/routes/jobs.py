from fastapi import APIRouter, Depends,BackgroundTasks
from sqlalchemy.orm import Session
from ..models import Job
from fastapi.responses import JSONResponse
from ..database import get_db
from ..ai import analyze_job_with_ai
from ..schemas import JobCreate,JobResponse
from ..scrapers import fetch_all_greenhouse_jobs
from ..crud import create_job, get_jobs


from ..verifier import (
    detect_scam_phrases,
    check_remote_validity,
    calculate_score,
    
    clean_description,
    extract_summary
)


def safe_truncate(value, max_length=255, default=""):
  
    # Handle None values
    if value is None:
        return default[:max_length] if default else ""
    
    # Convert non-string types to string
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return default[:max_length] if default else ""
    
    return value[:max_length]

router = APIRouter()

@router.get("/")
def all_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()
    return {"jobs": jobs, "count": len(jobs)}



@router.post("/",response_model=JobResponse)
def create_new_job(job: JobCreate, db: Session = Depends(get_db)):

    
    # Run scam detection on the submitted job
    flags = detect_scam_phrases(job.description)
    verified_remote = check_remote_validity(job.description)
    score = calculate_score(flags, verified_remote)
    
    # Create job data dictionary
    job_data = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "source": job.source,
        "description": job.description,
        "legitimacy_score": score,
        "legitimacy_reason": f"Scam flags: {len(flags)}. Remote valid: {verified_remote}",
        "verified_remote": verified_remote,
        "scam_flag": len(flags) > 0,
    }
    
    # Save using your CRUD function
    created_job = create_job(db, job_data)
    return created_job


@router.post("/scrape")
async def run_scraper_in_background():
    """This runs in the background"""
    from ..database import SessionLocal  # Import here to avoid circular imports
    
    db = SessionLocal()
    
    try:
        print("🔄 Background scraper started...")
        
        jobs = await fetch_all_greenhouse_jobs(limit_per_company=1)
        saved_count = 0
        error_count = 0
        duplicate_count=0
        for api_job in jobs:
            try:
                greenhouse_job_id = str(api_job.get('id'))
                title = api_job.get('title', '')
                if not title:
                    title = "Untitled Position"
                
                company = api_job.get('company_board', 'Unknown Company')
                
                
                raw_description = api_job.get('content') or api_job.get('description') or ''
                
                # CLEAN AND SHORTEN description (max 1500 chars)
                description = clean_description(raw_description, max_length=1500)
                
                # Also create a very short summary (max 300 chars) for preview
                short_summary = extract_summary(raw_description, max_length=300)
                
                if not description or len(description) < 50:
                    print(f"  No valid description for {title}, skipping...")
                    continue
                
                # Get location (might be nested)
                location = api_job.get('location', {})
                if isinstance(location, dict):
                    location = location.get('name', 'Remote')
                elif not location:
                    location = 'Remote'

                apply_url = api_job.get('absolute_url', '')
                if not apply_url:
                    # Fallback: construct URL if not provided
                    job_id = api_job.get('id')
                    if job_id and company:
                        apply_url = f"https://boards.greenhouse.io/{company}/jobs/{job_id}"
                    else:
                        apply_url = "#"
                
                existing = db.query(Job).filter(
                    Job.source_job_id == greenhouse_job_id
                ).first()
                
                if existing:
                    print(f"    ⏭️ Duplicate skipped: {title} (ID: {greenhouse_job_id})")
                    duplicate_count += 1
                    continue

                # Run scam detection on the full description
                flags = detect_scam_phrases(description)
                verified_remote = check_remote_validity(description)
                score = calculate_score(flags, verified_remote)
                
                ai_result = analyze_job_with_ai(description)
                
                # Create and save job
                job_data = {
                    "title": title[:255],
                    "company": company[:255],
                    "location": location[:255] if location else "Remote",
                    "salary": "Not specified",
                    "source": "Greenhouse",
                    "description": short_summary,
                    "legitimacy_score": score,
                    "legitimacy_reason": f"Scam flags: {len(flags)}. Remote valid: {verified_remote}",
                    "verified_remote": verified_remote,
                    "ai_analysis_raw": ai_result,
                    "scam_flag": len(flags) > 0,
                    "apply_url": apply_url,
                    "source_job_id":greenhouse_job_id, 
                }
                
                create_job(db, job_data)
                saved_count += 1
                
                if saved_count <= 5:
                    print(f"    Saved: {title} (Description length: {len(description)})")
                
            except Exception as e:
                error_count += 1
                print(f"   Error: {e}")
                continue
        
        print(f"\n Summary: Saved {saved_count} jobs, Errors: {error_count}")
        
    finally:
        db.close()


@router.post("/scrape/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Start scraper in background"""
    background_tasks.add_task(run_scraper_in_background)
    return {"message": "Scraping started in background"}