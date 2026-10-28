from fastapi import FastAPI, UploadFile, File, HTTPException
from app.predictor import ResumePredictor
from app.ocr import extract_resume_text
import shutil
import os
import uuid
import traceback
from fastapi.middleware.cors import CORSMiddleware
from app.job_api import search_jobs
from pydantic import BaseModel
from app.job_formatter import format_job_name

# ===========================================
# FastAPI App
# ===========================================

app = FastAPI(
    title="Resume Recommendation API",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "https://resume-job-recommendation-applicati.vercel.app"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)
# ===========================================
# Load Predictor Once
# ===========================================

predictor = ResumePredictor()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# ===========================================
# Request Model
# ===========================================

# class ResumeRequest(BaseModel):
#     resume_text: str

# ===========================================
# Home Route
# ===========================================

@app.get("/")
def home():
    return {
        "message": "Resume Recommendation API Running Successfully"
    }

# ===========================================
# Prediction Route
# ===========================================

@app.post("/predict")
async def predict(file: UploadFile = File(...)):

    # Allowed extensions
    allowed_extensions = [".pdf", ".docx"]

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported."
        )

    # Unique filename
    unique_filename = f"{uuid.uuid4()}{extension}"

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:

        # OCR
        resume_text = extract_resume_text(file_path)

        # Recommendation
        result = predictor.predict(resume_text)

        return result

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if os.path.exists(file_path):
            os.remove(file_path)

class LiveJobsRequest(BaseModel):

    recommendations: list
@app.post("/live-jobs")
async def live_jobs(request: LiveJobsRequest):
    print("LIVE JOBS ENDPOINT CALLED")
    print(request.recommendations)
    try:
        all_jobs = []

        for recommendation in request.recommendations[:3]:

            role = format_job_name(recommendation["job_role"])

            print("Searching: ", role)

            jobs = search_jobs(role)

            all_jobs.extend(jobs)

        return {
            "success": True,
            "jobs": all_jobs
        }

    except Exception as e:
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e)
        }


@app.get("/debug-origin")
async def debug_origin():
    return {
        "allowed_origins": [
            "http://localhost:5173",
            "https://resume-job-recommendation-applicati.vercel.app"
        ]
    }