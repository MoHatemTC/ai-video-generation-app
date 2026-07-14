import os

from dotenv import load_dotenv

load_dotenv()  # must run before any module reads os.getenv for API keys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.routes import intake, videos

app = FastAPI(title=os.getenv("APP_NAME", "Sprints Video Studio"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin before production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": app.title}


app.include_router(intake.router)
app.include_router(videos.router)
