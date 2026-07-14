import os
from fastapi import FastAPI
from dotenv import load_dotenv

# Import the router we just created
from backend.routes.video_routes import router as video_router
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Initialize API
app = FastAPI(
    title="Sprints Video Studio API",
    description="Backend orchestration for AI video generation."
)

# Add CORS Middleware to allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace "*" with the React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routes from the routes/ folder (following company rules!)
app.include_router(video_router)

@app.get("/")
def read_root():
    return {"message": "Sprints Video Studio API is running!"}