import httpx
from typing import List, Dict, Any
import asyncio

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

async def fetch_greenhouse_jobs(company_board: str) -> List[Dict[str, Any]]:
    """Fetch job listings from a single company's Greenhouse board"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_board}/jobs"
    
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            for job in jobs:
                job['company_board'] = company_board
            return jobs
        return []

async def fetch_job_details(company_board: str, job_id: int) -> Dict[str, Any]:
    """Fetch FULL details for a specific job including description"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_board}/jobs/{job_id}"
    
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30.0  # Add timeout
        ) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  Job {job_id} returned status {response.status_code}")
                return {}
                
    except httpx.TimeoutException:
        print(f"  Timeout fetching job {job_id}")
        return {}
    except httpx.ConnectError:
        print(f"   Connection error for {company_board}")
        return {}
    except Exception as e:
        print(f"   Error fetching job {job_id}: {type(e).__name__}: {e}")
        return {}

async def fetch_all_greenhouse_jobs(limit_per_company: int = 10) -> List[Dict[str, Any]]:
    """Fetch jobs from all companies WITH full descriptions"""
    all_jobs = []
    
    for company in TECH_COMPANIES:
        print(f"Fetching jobs from {company}...")
        
        # Get basic job listings
        jobs = await fetch_greenhouse_jobs(company)
        
        if not jobs:
            print(f"   No jobs found for {company}")
            continue
        
        print(f"   Found {len(jobs[:limit_per_company])} jobs, fetching details...")
        
        # For each job, fetch full details
        for job in jobs[:limit_per_company]:
            job_id = job.get('id')
            if job_id:
                # Get full job details with description
                full_job = await fetch_job_details(company, job_id)
                if full_job:
                    # Merge basic info with full details
                    full_job['company_board'] = company
                    all_jobs.append(full_job)
                    print(f"       Fetched: {full_job.get('title', 'Unknown')}")
                else:
                    print(f"      Failed to fetch details for job {job_id}")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    print(f"\nTotal jobs with descriptions: {len(all_jobs)}")
    return all_jobs



#async def fetch_remote_ok_jobs():
    #url = "https://remoteok.com/api"

   # async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
       # res = await client.get(url)
      #  data = res.json()

   # return data[1:]

