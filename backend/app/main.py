from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from .database import Base, engine
from .routes.jobs import router as jobs_router

# Create tables
Base.metadata.create_all(bind=engine)

# Define lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the server STARTS
    print("🚀 Server starting, beginning initial scrape...")
    
    # Start scraper in background (don't wait)
    asyncio.create_task(run_initial_scrape())
    
    yield  # Server runs here
    
    # This runs when server shuts down
    print("👋 Server shutting down...")

async def run_initial_scrape():
    """Run scraper once when server starts"""
    try:
        from .routes.jobs import run_scraper_in_background
        await run_scraper_in_background()
    except Exception as e:
        print(f"Initial scrape failed: {e}")


app = FastAPI(
    title="Remote Job Verifier API",
    lifespan=lifespan  # Attach lifespan here
)


app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

print("🔥 MAIN LOADED")

@app.get("/")
def root():
    return {
        "message": "Remote Job Verifier API Running"
    }