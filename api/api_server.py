from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import uuid
import sys
import os
import json

# Add parent directory to path to import grader and database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grader import grade_submission
from database import init_db, create_user, verify_user, save_submission, get_leaderboard_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initializes the database on application startup."""
    init_db()

class Submission(BaseModel):
    user_id: str
    problem_id: str
    code: str

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
async def root():
    return {"message": "Coding Challenge API is running!", "status": "ok"}

@app.post("/signup")
async def signup(request: SignupRequest):
    """User signup"""
    result = create_user(request.username, request.email, request.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/login")
async def login(request: LoginRequest):
    """User login"""
    result = verify_user(request.username, request.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.post("/submit")
async def submit_code(submission: Submission):
    # locate test_cases/<problem_id>.json
    test_case_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_cases", f"{submission.problem_id}.json")
    if not os.path.exists(test_case_path):
        raise HTTPException(status_code=404, detail="Problem test cases not found")

    # Grade submission
    result = grade_submission(
        code=submission.code,
        problem_id=submission.problem_id,
        user_id=submission.user_id
    )

    # Save to database
    submission_entry = result["submission_entry"]
    submission_entry["timestamp"] = datetime.now() # Ensure timestamp is a datetime object
    
    save_result = save_submission(submission_entry)
    if not save_result["success"]:
        raise HTTPException(status_code=500, detail=f"Database error: {save_result['error']}")

    return {"grade": result, "leaderboard_entry": submission_entry}

@app.get("/leaderboard")
async def get_leaderboard():
    """Get current leaderboard standings from the database"""
    result = get_leaderboard_data()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Database error: {result['error']}")
        
    return {"leaderboard": result["leaderboard"]}

@app.get("/problems")
def list_problems():
    problems = []
    test_cases_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_cases")
    for file in os.listdir(test_cases_dir):
        if file.endswith(".json"):
            try:
                with open(os.path.join(test_cases_dir, file), "r") as f:
                    data = json.load(f)
                if "public_tests" in data or "hidden_tests" in data:
                        problems.append(file.replace(".json", ""))
            except Exception as e:
                continue  # skip invalid JSON files
    return {"problems": problems}

@app.get("/problem/{problem_id}")
def get_problem_details(problem_id: str):
    """Get detailed information about a specific problem"""
    try:
        test_case_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_cases", f"{problem_id}.json")
        if not os.path.exists(test_case_path):
            raise HTTPException(status_code=404, detail="Problem not found")
        
        with open(test_case_path, "r") as f:
            problem_data = json.load(f)
        
        return {
            "problem_id": problem_id,
            "public_tests": problem_data.get("public_tests", []),
            "hidden_tests_count": len(problem_data.get("hidden_tests", [])),
            "total_tests": len(problem_data.get("public_tests", [])) + len(problem_data.get("hidden_tests", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading problem: {str(e)}")

# For Vercel deployment
app = app