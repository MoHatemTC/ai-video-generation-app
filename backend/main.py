import os
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Import the router we just created
from backend.routes.video_routes import router as video_router

load_dotenv()

# Setup litellm settings safely if installed
try:
    import litellm
    litellm.drop_params = True
except ImportError:
    pass

# Read the frontend URL from environment, default to localhost for development
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Initialize API
app = FastAPI(
    title="Sprints Video Studio API",
    description="Backend orchestration for AI video generation."
)

# Add CORS Middleware to allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Include the routes from the routes/ folder (following company rules!)
app.include_router(video_router)

# Mount static renders and storage directories if available
renders_dir = os.path.join(os.path.dirname(__file__), "..", "data", "renders")
os.makedirs(renders_dir, exist_ok=True)
app.mount("/renders", StaticFiles(directory=renders_dir), name="renders")

@app.get("/")
def read_root():
    return {"message": "Sprints Video Studio API is running!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}