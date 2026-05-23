import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from .english import is_english

from .models import Job  # Replace with your actual path
from .crud import create_job  # Replace with your actual path

TECH_COMPANIES = [
    "stripe",
    "gitlab", 
    "shopify",
    "automattic",
    "dropbox",
    "airbnb",
    "slack",
    "cloudflare",
    "cockroachlabs",
    "retool",
    "vercel",
    "notion",
    "figma",
    "canva",
    "atlassian",
    "mongodb",
    "elastic",
    "datadog",
    "confluent",
    "hashicorp"
]


async def fetch_remoteok_jobs(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetch raw job listings from Remote OK API"""
    url = "https://remoteok.com/api"
    
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                # Skip header and apply offset/limit
                jobs = data[1:]  # Get all jobs
                # Apply offset (skip first N jobs)
                if offset:
                    jobs = jobs[offset:]
                # Apply limit
                if limit:
                    jobs = jobs[:limit]
            else:
                jobs = []
            return jobs
        else:
            print(f"Remote OK API returned status {response.status_code}")
            return []

async def fetch_all_remoteok_jobs(
    db: Session, 
    batch_size: int = 50,
    max_batches: int = 5,
    only_english: bool = True  
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from Remote OK, checking for duplicates and filtering by language
    
    Args:
        db: Database session
        batch_size: Number of jobs to fetch per batch
        max_batches: Maximum number of batches to fetch
        only_english: If True, only return English jobs
    """
    # Get existing job IDs from database
    existing_ids: Set[str] = set()
    try:
        existing_jobs = db.query(Job.source_job_id).filter(Job.source == "RemoteOK").all()
        for job in existing_jobs:
            if job.source_job_id:
                existing_ids.add(str(job.source_job_id))
        print(f"📊 Found {len(existing_ids)} existing RemoteOK jobs in database")
    except Exception as e:
        print(f"⚠️ Error querying existing jobs: {e}")
        existing_ids = set()
    
    all_new_jobs = []
    offset = 0
    batch_num = 1
    skipped_non_english = 0  # Track non-English jobs skipped
    
    while batch_num <= max_batches:
        print(f"\n🔍 Fetching batch {batch_num} (offset: {offset}, size: {batch_size})...")
        
        # Fetch a batch of jobs
        raw_jobs = await fetch_remoteok_jobs(limit=batch_size, offset=offset)
        
        if not raw_jobs:
            print("❌ No more jobs available from API")
            break
        
        print(f"📥 Fetched {len(raw_jobs)} jobs in batch {batch_num}")
        
        # Check for new jobs in this batch
        new_jobs_in_batch = []
        for raw_job in raw_jobs:
            job_id = str(raw_job.get("id"))
            
            # Skip if already in database
            if job_id in existing_ids:
                continue
            
            # Get title and description for language check
            title = raw_job.get("position") or raw_job.get("title") or ""
            description = raw_job.get("description") or ""
            
            # Check language if required
            if only_english:
                # Combine title and description for better detection
                text_to_check = f"{title} {description}"
                
                if not is_english(text_to_check):
                    skipped_non_english += 1
                    if skipped_non_english <= 5:  # Show first 5 skipped jobs
                        print(f"   ⏭️ Skipping non-English job: {title[:50]}...")
                    continue
            
            # Normalize the job
            normalized_job = {
                "id": raw_job.get("id"),
                "title": title or "Untitled Position",
                "company_board": raw_job.get("company") or "Unknown Company",
                "content": description,
                "description": description,
                "absolute_url": raw_job.get("url") or "",
                "location": raw_job.get("location") or "Remote",
                "company": raw_job.get("company"),
                "position": raw_job.get("position"),
                "url": raw_job.get("url"),
                "tags": raw_job.get("tags", []),
                "date_posted": raw_job.get("date") or raw_job.get("posted"),
            }
            
            new_jobs_in_batch.append(normalized_job)
            existing_ids.add(job_id)  # Add to set to avoid duplicates in same session
        
        print(f"✨ Found {len(new_jobs_in_batch)} new English jobs in batch {batch_num}")
        
        all_new_jobs.extend(new_jobs_in_batch)
        
        # If we found new jobs, we can stop
        if new_jobs_in_batch:
            print(f"✅ Found {len(new_jobs_in_batch)} new English jobs, stopping fetch")
            break
        
        # If no new jobs found, move to next batch
        print(f"⚠️ No new English jobs in batch {batch_num}, fetching older jobs...")
        offset += batch_size
        batch_num += 1
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    if skipped_non_english > 0:
        print(f"\n📊 Skipped {skipped_non_english} non-English jobs")
    
    if not all_new_jobs:
        print("\n✨ No new English jobs found after checking all batches")
    else:
        print(f"\n📊 Total new English jobs found: {len(all_new_jobs)}")
    
    return all_new_jobs