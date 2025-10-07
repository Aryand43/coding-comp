import psycopg2
from psycopg2.extras import RealDictCursor
import os
from passlib.context import CryptContext
from datetime import datetime
import json

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Database connection string will be provided by Railway environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Get database connection"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create submissions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id UUID PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            problem_id VARCHAR(100) NOT NULL,
            score INTEGER NOT NULL,
            replay_result VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_details TEXT,
            UNIQUE (user_id, problem_id)
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

def create_user(username: str, email: str, password: str):
    """Create new user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            truncated_bytes = password_bytes[:72]
            while truncated_bytes:
                try:
                    password = truncated_bytes.decode('utf-8')
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
        
        hashed_password = pwd_context.hash(password)
        
        cur.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s) RETURNING id",
            (username, email, hashed_password)
        )
        user_id = cur.fetchone()['id']
        conn.commit()
        return {"success": True, "user_id": user_id, "username": username}
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        error_msg = str(e)
        if "username" in error_msg:
            return {"success": False, "error": "Username already exists"}
        elif "email" in error_msg:
            return {"success": False, "error": "Email already exists"}
        else:
            return {"success": False, "error": "Username or email already exists"}
            
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Error: {str(e)}"}
        
    finally:
        cur.close()
        conn.close()

def verify_user(username: str, password: str):
    """Verify user credentials"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            return {"success": False, "error": "Invalid credentials"}
        
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            truncated_bytes = password_bytes[:72]
            while truncated_bytes:
                try:
                    password = truncated_bytes.decode('utf-8')
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
        
        if pwd_context.verify(password, user['hashed_password']):
            return {
                "success": True, 
                "user_id": user['id'], 
                "username": user['username'], 
                "email": user['email']
            }
        else:
            return {"success": False, "error": "Invalid credentials"}
            
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
        
    finally:
        cur.close()
        conn.close()

def save_submission(submission_entry: dict):
    """Save a submission to the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO submissions (id, user_id, problem_id, score, replay_result, timestamp, error_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, problem_id) DO UPDATE SET
                score = EXCLUDED.score,
                replay_result = EXCLUDED.replay_result,
                timestamp = EXCLUDED.timestamp,
                error_details = EXCLUDED.error_details
            WHERE EXCLUDED.score > submissions.score OR (EXCLUDED.score = submissions.score AND EXCLUDED.timestamp < submissions.timestamp)
            """,
            (
                submission_entry["submission_id"],
                submission_entry["user_id"],
                submission_entry["problem_id"],
                submission_entry["score"],
                submission_entry["replay_result"],
                submission_entry["timestamp"],
                json.dumps(submission_entry.get("error_details", []))
            )
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

def get_leaderboard_data():
    """Retrieve all submissions and format for leaderboard"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # This query gets the latest best score per user for each problem
        cur.execute("""
            SELECT
                id, user_id, problem_id, score, replay_result, timestamp
            FROM (
                SELECT
                    id, user_id, problem_id, score, replay_result, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY user_id, problem_id ORDER BY score DESC, timestamp ASC) as rn
                FROM submissions
            ) as t
            WHERE t.rn = 1
            ORDER BY score DESC, timestamp ASC
        """)
        submissions_by_problem = cur.fetchall()
        
        # Now, aggregate to get the single best score per user across all problems
        leaderboard = []
        seen = set()
        for entry in submissions_by_problem:
            if entry['user_id'] not in seen:
                leaderboard.append(dict(entry))
                seen.add(entry['user_id'])
                
        return {"success": True, "leaderboard": leaderboard}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()