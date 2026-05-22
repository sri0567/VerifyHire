import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routes.jobs import router as jobs_router

# Create tables at startup.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting, kicking off initial scrape...")
    asyncio.create_task(run_initial_scrape())
    yield
    print("Server shutting down...")


async def run_initial_scrape():
    try:
        from .routes.jobs import run_scraper_in_background

        await run_scraper_in_background()
    except Exception as exc:
        print(f"Initial scrape failed: {exc}")


app = FastAPI(title="Remote Job Verifier API", lifespan=lifespan)

frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])


@app.get("/")
def root():
    return {"message": "Remote Job Verifier API running"}