
# app.py (Multi-user version with Groq API, Database, and Authentication)
from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel
import requests

# Use database instead of JSON files
from database import (
    DatabaseBackedMemory as Memory,
    DatabaseBackedKnowledgeStore as KnowledgeStore,
    init_db,
    User,
    SessionLocal
)
from tools import get_time, get_time_human_short
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
import os
import sys
import subprocess
import threading
import time
from groq import Groq

# Authentication imports
from auth import (
    get_current_user,
    get_current_user_optional,
    create_user,
    authenticate_user,
    create_access_token,
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    get_db
)
from sqlalchemy.orm import Session

# Initialize database on startup
init_db()


app = FastAPI()

# Enable CORS for the popup UI to work from any origin
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow popup from any website
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SECURITY: Network-Only Mode =====
NETWORK_ONLY_MODE = os.getenv('GREENIE_NETWORK_ONLY', 'false').lower() == 'true'
ALLOWED_EXTERNAL_APIS = {
    'api.groq.com',  # Groq API (LLM)
}

def is_private_ip(ip_str: str) -> bool:
    """Check if IP is on private/internal network"""
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except:
        return False

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    if request.client:
        return request.client.host
    return '0.0.0.0'

@app.middleware("http")
async def network_security_middleware(request: Request, call_next):
    """Enforce network-only mode if enabled"""
    if NETWORK_ONLY_MODE:
        client_ip = get_client_ip(request)
        
        # Allow localhost and private IPs
        if not is_private_ip(client_ip):
            return JSONResponse(
                status_code=403,
                content={"error": "Network-only mode: Access restricted to internal network"}
            )
    
    response = await call_next(request)
    return response

# basic logging
import logging
logging.basicConfig(level=logging.INFO, filename=os.path.join(os.path.dirname(__file__), 'greenie.log'), filemode='a', format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('greenie')

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log full traceback for debugging
    tb = ''.join(__import__('traceback').format_exception(type(exc), exc, exc.__traceback__))
    logger.exception('Unhandled exception on %s %s: %s', request.method, request.url, tb)
    try:
        with open(os.path.join(os.path.dirname(__file__), 'error.log'), 'a', encoding='utf-8') as f:
            f.write(tb + '\n')
    except Exception:
        logger.exception('Failed to write to error.log')
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})

# support PyInstaller-frozen apps by resolving the base directory
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# serve static directories
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception:
        pass

# also serve assets if present
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Memory and knowledge store already initialized at top of file
# ephemeral in-memory session store: session_id -> list of {'role': 'user'|'assistant', 'text': str}
sessions: dict[str, list[dict]] = {}
SESSION_MAX = 10
last_prompt: str | None = None

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        # avoid raising FileNotFoundError which results in 500; return friendly JSON
        return JSONResponse(status_code=200, content={"error": "UI not available: static/index.html not found"})
    return FileResponse(index_path)

@app.get("/overlay")
async def overlay():
    """Serve the lightweight overlay UI.
    Falls back to main index if overlay file not present.
    """
    path = os.path.join(STATIC_DIR, "overlay.html")
    if os.path.exists(path):
        return FileResponse(path)
    # fallback: return the main UI
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=200, content={"error": "UI not available: static/overlay.html not found"})

@app.get("/chat-ui")
async def chat_popup():
    """Serve the chat popup UI with auth"""
    path = os.path.join(STATIC_DIR, "chat.html")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"error": "Chat UI not found"})

@app.get("/health")
async def health(request: Request):
    """Health check endpoint with Groq API status and security info."""
    client_ip = get_client_ip(request)
    is_private = is_private_ip(client_ip)
    
    status = {
        "ok": True,
        "groq_configured": bool(GROQ_API_KEY),
        "model": DEFAULT_MODEL,
        "security": {
            "network_only_mode": NETWORK_ONLY_MODE,
            "client_ip": client_ip,
            "is_private_network": is_private
        }
    }
    
    # Just report configuration status, don't test API on every health check
    # (avoids rate limiting and slow responses)
    if GROQ_API_KEY:
        status["groq_status"] = "configured"
    else:
        status["groq_status"] = "not_configured"
    
    return status

@app.get("/security/status")
async def security_status(request: Request):
    """Get current security status and restrictions"""
    client_ip = get_client_ip(request)
    is_private = is_private_ip(client_ip)
    
    return {
        "network_only_mode": NETWORK_ONLY_MODE,
        "client_ip": client_ip,
        "is_private_network": is_private,
        "access_allowed": not NETWORK_ONLY_MODE or is_private,
        "allowed_external_apis": list(ALLOWED_EXTERNAL_APIS)
    }


# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate email domain
    try:
        user_data.validate_email_domain()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    user = create_user(db, user_data.username, user_data.email, user_data.password)
    return user


@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token"""
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


# ===== ADMIN ENDPOINTS =====

@app.get("/admin/users")
async def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all users (admin only)"""
    # Get all users
    users = db.query(User).all()
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a user (admin only)"""
    # Prevent self-deletion
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted successfully"}


# ===== ERROR LOGGING ENDPOINTS =====

@app.post("/api/log-error")
async def log_error(
    error_data: dict,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Log an error from the client app"""
    from database import ErrorLog
    import json
    
    try:
        log = ErrorLog(
            user_id=current_user.id if current_user else None,
            error_message=error_data.get("message", "Unknown error"),
            error_type=error_data.get("type", "unknown"),
            error_details=json.dumps(error_data.get("details", {}))
        )
        db.add(log)
        db.commit()
        return {"status": "logged", "id": log.id}
    except Exception as e:
        db.rollback()
        print(f"Error logging error: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.get("/admin/logs")
async def get_error_logs(
    limit: int = 100,
    offset: int = 0,
    error_type: str = None,
    user_id: int = None,
    resolved: str = None,
    db: Session = Depends(get_db)
):
    """Get error logs (public for monitoring)"""
    from database import ErrorLog
    
    query = db.query(ErrorLog)
    
    # Filters
    if error_type:
        query = query.filter(ErrorLog.error_type == error_type)
    if user_id:
        query = query.filter(ErrorLog.user_id == user_id)
    if resolved:
        query = query.filter(ErrorLog.resolved == resolved)
    
    # Count total
    total = query.count()
    
    # Get paginated results
    logs = query.order_by(ErrorLog.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else "Anonymous",
                "error_message": log.error_message,
                "error_type": log.error_type,
                "error_details": log.error_details,
                "resolved": log.resolved,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


@app.get("/admin/logs/{log_id}")
async def get_error_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific error log (public for monitoring)"""
    from database import ErrorLog
    
    log = db.query(ErrorLog).filter(ErrorLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.user.username if log.user else "Anonymous",
        "error_message": log.error_message,
        "error_type": log.error_type,
        "error_details": log.error_details,
        "resolved": log.resolved,
        "created_at": log.created_at.isoformat() if log.created_at else None
    }


@app.patch("/admin/logs/{log_id}")
async def update_error_log(
    log_id: int,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update error log status (mark as resolved, etc) (admin only)"""
    from database import ErrorLog
    
    log = db.query(ErrorLog).filter(ErrorLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    if "resolved" in update_data:
        log.resolved = update_data["resolved"]  # "open", "investigating", "resolved"
    
    db.commit()
    return {"status": "updated", "id": log.id}


@app.get("/admin/logs/stats/summary")
async def get_error_stats(
    db: Session = Depends(get_db)
):
    """Get error statistics (public for monitoring)"""
    from database import ErrorLog
    from sqlalchemy import func
    
    # Total errors
    total_errors = db.query(ErrorLog).count()
    
    # Errors by type
    errors_by_type = db.query(
        ErrorLog.error_type,
        func.count(ErrorLog.id).label("count")
    ).group_by(ErrorLog.error_type).all()
    
    # Open errors
    open_errors = db.query(ErrorLog).filter(ErrorLog.resolved == "open").count()
    
    # Errors in last 24 hours
    from datetime import datetime, timedelta
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_errors = db.query(ErrorLog).filter(
        ErrorLog.created_at >= twenty_four_hours_ago
    ).count()
    
    # Most active error user
    most_active = db.query(
        ErrorLog.user_id,
        User.username,
        func.count(ErrorLog.id).label("count")
    ).join(User).group_by(ErrorLog.user_id, User.username).order_by(
        func.count(ErrorLog.id).desc()
    ).first()
    
    return {
        "total_errors": total_errors,
        "open_errors": open_errors,
        "recent_errors_24h": recent_errors,
        "errors_by_type": {et[0]: et[1] for et in errors_by_type},
        "most_active_error_user": {
            "user_id": most_active[0],
            "username": most_active[1],
            "error_count": most_active[2]
        } if most_active else None
    }


@app.get("/admin")
async def admin_dashboard():
    """Admin dashboard for error logs and monitoring (public access for team)"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Greenie Admin Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                color: #e0e0e0;
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            h1 {
                color: #00ff00;
                margin-bottom: 30px;
                text-align: center;
                font-size: 2.5em;
                text-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .stat-card {
                background: rgba(0, 0, 0, 0.3);
                border: 2px solid rgba(0, 255, 0, 0.3);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
            }
            
            .stat-card h3 {
                color: #00ff00;
                font-size: 0.9em;
                margin-bottom: 10px;
                text-transform: uppercase;
            }
            
            .stat-card .value {
                font-size: 2.5em;
                color: #00ff00;
                font-weight: bold;
            }
            
            .logs-section {
                background: rgba(0, 0, 0, 0.3);
                border: 2px solid rgba(0, 255, 0, 0.3);
                border-radius: 10px;
                padding: 20px;
            }
            
            .logs-section h2 {
                color: #00ff00;
                margin-bottom: 20px;
                border-bottom: 2px solid rgba(0, 255, 0, 0.3);
                padding-bottom: 10px;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            
            thead {
                background: rgba(0, 255, 0, 0.1);
            }
            
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(0, 255, 0, 0.2);
            }
            
            th {
                color: #00ff00;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 0.85em;
            }
            
            tr:hover {
                background: rgba(0, 255, 0, 0.05);
            }
            
            .error-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: bold;
            }
            
            .error-badge.network {
                background: rgba(255, 100, 100, 0.3);
                color: #ff6464;
            }
            
            .error-badge.timeout {
                background: rgba(255, 150, 0, 0.3);
                color: #ff9600;
            }
            
            .error-badge.auth {
                background: rgba(100, 100, 255, 0.3);
                color: #6464ff;
            }
            
            .error-badge.chat {
                background: rgba(255, 100, 200, 0.3);
                color: #ff64c8;
            }
            
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: bold;
            }
            
            .status-badge.open {
                background: rgba(255, 100, 100, 0.3);
                color: #ff6464;
            }
            
            .status-badge.investigating {
                background: rgba(255, 150, 0, 0.3);
                color: #ff9600;
            }
            
            .status-badge.resolved {
                background: rgba(0, 255, 100, 0.3);
                color: #00ff64;
            }
            
            .loading {
                text-align: center;
                color: #00ff00;
                padding: 40px;
            }
            
            .spinner {
                border: 3px solid rgba(0, 255, 0, 0.2);
                border-top: 3px solid #00ff00;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .refresh-btn {
                background: rgba(0, 255, 0, 0.2);
                border: 2px solid #00ff00;
                color: #00ff00;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                float: right;
                margin-bottom: 20px;
            }
            
            .refresh-btn:hover {
                background: rgba(0, 255, 0, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🟢 Greenie Admin Dashboard</h1>
            
            <button class="refresh-btn" onclick="loadStats()">🔄 Refresh</button>
            <div style="clear: both;"></div>
            
            <div class="stats-grid" id="statsGrid">
                <div class="loading">
                    <div class="spinner"></div>
                    Loading statistics...
                </div>
            </div>
            
            <div class="logs-section">
                <h2>Recent Error Logs</h2>
                <div id="logsContent">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading logs...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/admin/logs/stats/summary');
                    const data = await response.json();
                    
                    const statsHtml = `
                        <div class="stat-card">
                            <h3>Total Errors</h3>
                            <div class="value">${data.total_errors}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Open Errors</h3>
                            <div class="value">${data.open_errors}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Errors (24h)</h3>
                            <div class="value">${data.recent_errors_24h}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Error Types</h3>
                            <div class="value">${Object.keys(data.errors_by_type).length}</div>
                        </div>
                    `;
                    
                    document.getElementById('statsGrid').innerHTML = statsHtml;
                } catch (error) {
                    console.error('Failed to load stats:', error);
                    document.getElementById('statsGrid').innerHTML = '<p>Failed to load statistics</p>';
                }
            }
            
            async function loadLogs() {
                try {
                    const response = await fetch('/admin/logs?limit=50');
                    const data = await response.json();
                    
                    if (data.logs.length === 0) {
                        document.getElementById('logsContent').innerHTML = '<p>No errors logged yet. Great job! 🎉</p>';
                        return;
                    }
                    
                    const logsHtml = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>User</th>
                                    <th>Error Type</th>
                                    <th>Message</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.logs.map(log => `
                                    <tr>
                                        <td>${new Date(log.created_at).toLocaleString()}</td>
                                        <td>${log.username}</td>
                                        <td><span class="error-badge ${log.error_type.split('_')[0]}">${log.error_type}</span></td>
                                        <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis;">${log.error_message}</td>
                                        <td><span class="status-badge ${log.resolved}">${log.resolved}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                    
                    document.getElementById('logsContent').innerHTML = logsHtml;
                } catch (error) {
                    console.error('Failed to load logs:', error);
                    document.getElementById('logsContent').innerHTML = '<p>Failed to load logs</p>';
                }
            }
            
            // Load data on page load
            window.addEventListener('load', () => {
                loadStats();
                loadLogs();
                
                // Refresh every 30 seconds
                setInterval(() => {
                    loadStats();
                    loadLogs();
                }, 30000);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ===== MEMORY & KNOWLEDGE ENDPOINTS =====

class ChatRequest(BaseModel):
    message: str
    model: str | None = None  # allow overriding the model per request
    save: bool = True         # whether to save the user message to memory (long-term)
    recent: int | None = None # how many recent memories to include in the prompt
    include_knowledge: bool = True  # whether to include knowledge search results in prompt
    knowledge_n: int | None = None  # how many knowledge results to include (defaults to 5)
    include_system: bool = True  # whether to include basic system identity/personality in prompt
    session_id: str | None = None  # client session id for ephemeral conversation memory
    conversation_mode: bool = True  # whether to include ephemeral session history in prompt (default ON)
    fast: bool = False  # prefer lower-latency, reduced-context responses (Fast Mode)

class MemoryAddRequest(BaseModel):
    text: str
    reason: str

class KnowledgeAddRequest(BaseModel):
    name: str
    description: str
    keywords: list[str] | None = None

class SearchRequest(BaseModel):
    query: str
    n: int | None = 5

class TopicRequest(BaseModel):
    topic: str | None = None
    reason: str | None = None

class SummarizeRequest(BaseModel):
    content: str
    model: str | None = None

class UpdateRequest(BaseModel):
    confirm: bool | None = None
    branch: str | None = None

class UncertaintyLogRequest(BaseModel):
    user_message: str
    reply: str
    ts: float

# Groq API configuration (free tier: 30 req/min, 14,400 tokens/min)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama3-70b-8192"  # Options: llama3-70b-8192, llama3-8b-8192, mixtral-8x7b-32768, gemma-7b-it

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

@app.post("/memory/add")
async def add_memory(req: MemoryAddRequest, current_user: User | None = Depends(get_current_user_optional)):
    """Add a memory (user-specific if authenticated)"""
    user_id = current_user.id if current_user else 1
    user_memory = Memory(user_id=user_id)
    user_memory.add_memory(req.text)
    return {"ok": True}

@app.get("/memory/recent")
async def recent_memories(n: int = 5, current_user: User | None = Depends(get_current_user_optional)):
    """Get recent memories (user-specific if authenticated)"""
    user_id = current_user.id if current_user else 1
    user_memory = Memory(user_id=user_id)
    return {"memories": user_memory.get_recent(n)}

@app.post("/knowledge/add")
async def add_knowledge(req: KnowledgeAddRequest, current_user: User | None = Depends(get_current_user_optional)):
    """Add knowledge entry (user-specific if authenticated)"""
    user_id = current_user.id if current_user else 1
    user_knowledge = KnowledgeStore(user_id=user_id)
    user_knowledge.add_knowledge(req.name, req.description, req.keywords)
    return {"ok": True}

@app.post("/knowledge/search")
async def search_knowledge(req: SearchRequest, current_user: User | None = Depends(get_current_user_optional)):
    """Search knowledge base (user-specific if authenticated)"""
    user_id = current_user.id if current_user else 1
    user_knowledge = KnowledgeStore(user_id=user_id)
    results = user_knowledge.search(req.query, req.n or 5)
    return {"results": results}

@app.get("/knowledge")
async def list_knowledge(current_user: User | None = Depends(get_current_user_optional)):
    """List all knowledge entries (user-specific if authenticated)"""
    user_id = current_user.id if current_user else 1
    user_knowledge = KnowledgeStore(user_id=user_id)
    return {"results": user_knowledge.list_all()}

@app.post("/tools/summarize")
async def summarize(req: SummarizeRequest):
    """Summarize a piece of text using the LLM."""
    if not groq_client:
        return {"error": "LLM service not configured"}
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize the following text:\n\n{req.content}"
                }
            ],
            model=DEFAULT_MODEL,
            temperature=0.5,
            max_tokens=512,
            timeout=60
        )
        return {"summary": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"error": f"Failed to summarize: {str(e)}"}

@app.get("/debug/last_prompt")
async def debug_last_prompt():
    return {"last_prompt": last_prompt}

@app.get('/debug/version')
async def debug_version():
    try:
        p = os.path.join(os.path.dirname(__file__), 'app.py')
        return {"version": os.path.getmtime(p)}
    except Exception:
        return {"version": None}


# Optional shutdown hook that can be registered by an in-process runner
shutdown_hook = None

# update confirmation state and last update record
pending_update_timestamp: float | None = None
pending_update_window = 60  # seconds to allow confirmation
last_update: dict | None = None


def register_shutdown_hook(fn):
    global shutdown_hook
    shutdown_hook = fn

# log runtime tmpdir when running frozen (onefile)
if getattr(sys, '_MEIPASS', None):
    try:
        logger.info('Running in PyInstaller onefile mode; runtime tmpdir: %s', getattr(sys, '_MEIPASS'))
    except Exception:
        pass


@app.post('/shutdown')
async def shutdown(request: Request):
    # allow shutdown only from localhost for safety
    client_host = request.client.host if request.client else None
    # allow local requests; in test environments request.client may be None or 'testclient'
    allowed_hosts = ("127.0.0.1", "::1", "localhost", "testclient")
    if client_host not in allowed_hosts and client_host is not None:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    # If an in-process shutdown hook is registered, call it to gracefully stop the server
    if shutdown_hook:
        try:
            import threading
            threading.Thread(target=shutdown_hook, daemon=True).start()
            return {"ok": True, "message": "Server shutting down (hook)"}
        except Exception as e:
            logger.exception('Shutdown hook failed: %s', e)
            return JSONResponse(status_code=500, content={"error": "Shutdown failed", "detail": str(e)})

    # fallback: force exit in a separate thread
    def _exit():
        import time, os
        time.sleep(0.2)
        os._exit(0)

    import threading
    threading.Thread(target=_exit, daemon=True).start()
    return {"ok": True, "message": "Server shutting down"}

def _build_prompt_and_payload(req: ChatRequest):
    # Build the prompt and base payload for both streaming and non-streaming endpoints
    recent_n = req.recent or 5
    try:
        if getattr(req, 'fast', False):
            recent_n = 0
            req.include_knowledge = False
    except Exception:
        pass
    mems = memory.get_recent(recent_n)
    mem_text = ""
    if mems:
        mem_text = "Memories:\n" + "\n".join(f"- {m}" for m in mems) + "\n\n"

    import re

    def extract_explicit_topic(msg: str) -> str | None:
        patterns = [
            r"(?:change topic to|switch to|focus on)\s+(.+)",
            r"(?:let(?:'s| us) talk about|talk about|now about|now let's talk about|discuss)\s+(.+)",
            r"^topic:\s*(.+)"
        ]
        for pat in patterns:
            m = re.search(pat, msg, re.I)
            if m:
                return m.group(1).strip().strip('."\'')
        moving_phrases = ["moving on", "new topic", "different topic", "anyway"]
        if any(p in msg.lower() for p in moving_phrases):
            return "__CLEAR__"
        return None

    explicit = extract_explicit_topic(req.message)
    current_topic = None
    try:
        from memory import get_topic, set_topic, clear_topic
        current_topic = get_topic()
    except Exception:
        current_topic = None

    if explicit == "__CLEAR__":
        try:
            clear_topic()
            current_topic = None
        except Exception:
            pass
    elif explicit:
        try:
            set_topic(explicit)
            current_topic = explicit
        except Exception:
            pass
    else:
        try:
            bm = user_knowledge.best_match(req.message)
        except Exception:
            bm = None
        if bm:
            name = bm.get('name')
            if name and name != current_topic:
                try:
                    set_topic(name)
                    current_topic = name
                except Exception:
                    pass

    topic_text = ""
    if current_topic:
        topic_text = f"Current topic: {current_topic}\n\n"

    system_text = ""
    try:
        time_info = get_time()
        time_text = f"Time:\n- {time_info['human_short']} (Europe/London)\n\n"
    except Exception:
        time_text = ""

    if getattr(req, "include_system", True):
        try:
            items = [
                it for it in user_knowledge.list_all()
                if ('identity' in [k.lower() for k in it.get('keywords', [])])
                or ('personality' in [k.lower() for k in it.get('keywords', [])])
                or (it.get('name','').lower().startswith('greenie'))
            ]
        except Exception:
            items = []
        if items:
            system_text = "System:\n" + "\n".join(f"- {it.get('name')}: {it.get('description','')}" for it in items) + "\n\n"
        else:
            system_text = "System:\n- Greenie: an AI assistant that is witty, intelligent, and supportive.\n\n"

    system_text = time_text + system_text

    knowledge_text = ""
    if getattr(req, "include_knowledge", True):
        k_n = req.knowledge_n or 5
        try:
            k_results = user_knowledge.search(req.message, k_n)
        except Exception:
            k_results = []
        if k_results:
            knowledge_text = "Knowledge:\n" + "\n".join(
                f"- {item.get('name', item.get('title', ''))}: {item.get('description', '')}"
                for item in k_results
            ) + "\n\n"

    session_text = ""
    try:
        if not getattr(req, 'fast', False) and getattr(req, 'conversation_mode', True) and getattr(req, 'session_id', None):
            hist = sessions.get(req.session_id, [])
            if hist:
                session_text = "Recent conversation:\n" + "\n".join(f"{itm['role']}: {itm['text']}" for itm in hist[-SESSION_MAX:]) + "\n\n"
    except Exception:
        session_text = ""

    prompt = system_text + topic_text + knowledge_text + mem_text + session_text + req.message

    payload = {
        "model": req.model or DEFAULT_MODEL,
        "prompt": prompt,
    }
    ol_timeout = 120
    try:
        if getattr(req, 'fast', False):
            ol_timeout = 30
            if not req.model:
                payload['model'] = 'llama3-8b-8192'  # Faster, smaller model for fast mode
    except Exception:
        pass

    return prompt, payload, ol_timeout


@app.post("/chat")
async def chat(req: ChatRequest, current_user: User | None = Depends(get_current_user_optional)):
    """
    Chat endpoint - works with or without authentication
    - Authenticated users get per-user memory/knowledge
    - Unauthenticated users use default user (ID=1) for backward compatibility
    """
    # Determine user ID (authenticated user or default)
    user_id = current_user.id if current_user else 1
    
    # Create user-specific memory and knowledge instances
    user_memory = Memory(user_id=user_id)
    user_knowledge = KnowledgeStore(user_id=user_id)
    
    try:
        # include recent memories at the top of the prompt
        recent_n = req.recent or 5
        # if fast mode requested, drop recent memories and knowledge to reduce latency
        try:
            if getattr(req, 'fast', False):
                recent_n = 0
                req.include_knowledge = False
        except Exception:
            pass
        mems = user_memory.get_recent(recent_n)
        mem_text = ""
        if mems:
            mem_text = "Memories:\n" + "\n".join(f"- {m}" for m in mems) + "\n\n"

        # detect explicit topic change phrases (e.g. 'talk about X', 'change topic to Y')
        import re

        def extract_explicit_topic(msg: str) -> str | None:
            patterns = [
                r"(?:change topic to|switch to|focus on)\s+(.+)",
                r"(?:let(?:'s| us) talk about|talk about|now about|now let's talk about|discuss)\s+(.+)",
                r"^topic:\s*(.+)"
            ]
            for pat in patterns:
                m = re.search(pat, msg, re.I)
                if m:
                    return m.group(1).strip().strip('."\'')
            # generic 'moving on' or 'different topic' phrases mean clear topic
            moving_phrases = ["moving on", "new topic", "different topic", "anyway"]
            if any(p in msg.lower() for p in moving_phrases):
                return "__CLEAR__"
            return None

        explicit = extract_explicit_topic(req.message)
        current_topic = None
        try:
            from memory import get_topic, set_topic, clear_topic
            current_topic = get_topic()
        except Exception:
            current_topic = None

        if explicit == "__CLEAR__":
            try:
                clear_topic()
                current_topic = None
            except Exception:
                pass
        elif explicit:
            # user explicitly set a topic
            try:
                set_topic(explicit)
                current_topic = explicit
            except Exception:
                pass
        else:
            # try to infer topic from knowledge store matches
            try:
                bm = user_knowledge.best_match(req.message)
            except Exception:
                bm = None
            if bm:
                name = bm.get('name')
                if name and name != current_topic:
                    try:
                        set_topic(name)
                        current_topic = name
                    except Exception:
                        pass

        # include the current topic in the prompt
        topic_text = ""
        if current_topic:
            topic_text = f"Current topic: {current_topic}\n\n"

        # include basic system identity/personality knowledge (always near top if requested)
        system_text = ""
        try:
            # include current UK time so model can reference it
            time_info = get_time()
            time_text = f"Time:\n- {time_info['human_short']} (Europe/London)\n\n"
        except Exception:
            time_text = ""

        if getattr(req, "include_system", True):
            try:
                items = [
                    it for it in user_knowledge.list_all()
                    if ('identity' in [k.lower() for k in it.get('keywords', [])])
                    or ('personality' in [k.lower() for k in it.get('keywords', [])])
                    or (it.get('name','').lower().startswith('greenie'))
                ]
            except Exception:
                items = []
            if items:
                system_text = "System:\n" + "\n".join(f"- {it.get('name')}: {it.get('description','')}" for it in items) + "\n\n"
            else:
                # fallback brief identity so model always knows its name
                system_text = "System:\n- Greenie: an AI assistant that is witty, intelligent, and supportive.\n\n"

        # prepend time information so it is always visible to the model
        system_text = time_text + system_text

        # include relevant knowledge items at the top of the prompt (if requested)
        knowledge_text = ""
        if getattr(req, "include_knowledge", True):
            k_n = req.knowledge_n or 5
            try:
                k_results = user_knowledge.search(req.message, k_n)
            except Exception:
                k_results = []
            if k_results:
                knowledge_text = "Knowledge:\n" + "\n".join(
                    f"- {item.get('name', item.get('title', ''))}: {item.get('description', '')}"
                    for item in k_results
                ) + "\n\n"

        # include session (ephemeral) history if conversation_mode is enabled and a session_id is passed
        session_text = ""
        try:
            # Skip including session history when fast mode requested to reduce prompt size & latency
            if not getattr(req, 'fast', False) and getattr(req, 'conversation_mode', True) and getattr(req, 'session_id', None):
                hist = sessions.get(req.session_id, [])
                if hist:
                    session_text = "Recent conversation:\n" + "\n".join(f"{itm['role']}: {itm['text']}" for itm in hist[-SESSION_MAX:]) + "\n\n"
        except Exception:
            session_text = ""

        prompt = system_text + topic_text + knowledge_text + mem_text + session_text + req.message

        payload = {
            "model": req.model or DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False  # single JSON response
        }
        # prefer a faster model and shorter read timeout if requested
        ol_timeout = 60
        try:
            if getattr(req, 'fast', False):
                ol_timeout = 30
                # prefer a quicker model option if not explicitly set
                if not req.model:
                    payload['model'] = 'llama3-8b-8192'  # Faster, smaller model
        except Exception:
            pass


        # If user asks Greenie to update itself, use a confirmation flow to avoid accidental updates
        import re
        update_patterns = [r"\b(update yourself|self-?update|pull latest|update greenie|update now)\b"]
        confirm_patterns = [r"\b(confirm update|confirm|yes update|yes, update|yes please update|go ahead update)\b"]
        global pending_update_timestamp, last_update

        # If user explicitly confirms and there is a recent pending request, perform update
        if any(re.search(p, req.message, re.I) for p in confirm_patterns):
            if pending_update_timestamp and (time.time() - pending_update_timestamp) <= pending_update_window:
                try:
                    res = _perform_git_update()
                    last_update = res
                    pending_update_timestamp = None
                    return {"reply": f"Update performed. Result: {res.get('summary','no output')}", "update": res}
                except Exception as e:
                    return {"error": f"Update failed: {e}"}
            else:
                return {"reply": "No recent update request found. Ask me to update yourself first by saying 'update yourself'."}

        # If user asks to update, prompt for confirmation and record timestamp
        if any(re.search(p, req.message, re.I) for p in update_patterns):
            pending_update_timestamp = time.time()
            return {"reply": "Are you sure? Reply 'confirm update' within 60 seconds to proceed."}

        try:
            # store the last prompt for debug purposes
            global last_prompt
            last_prompt = payload["prompt"]

            import time as _time
            start_time = _time.time()

            # testing hook and test-mode shortcut
            if os.environ.get('GREENIE_TEST_MODE') == '1':
                if req.message.strip().lower() == 'force timeout':
                    # simulate structured timeout response for tests
                    return {"error": "timeout", "message": f"Model timed out after {ol_timeout}s.", "suggestions": ["enable_fast", "retry"]}
                # when in test mode, return deterministic fake replies to avoid external dependency
                reply = f"Test reply: {req.message}"
            else:
                # Use Groq API instead of Ollama
                if not groq_client:
                    logger.error("Groq API key not set. Set GROQ_API_KEY environment variable.")
                    return {"error": "LLM service not configured. Please set GROQ_API_KEY environment variable."}
                
                try:
                    # Convert prompt to Groq chat format
                    chat_completion = groq_client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are Greenie, a helpful IT support assistant."
                            },
                            {
                                "role": "user",
                                "content": payload["prompt"]
                            }
                        ],
                        model=payload.get('model', DEFAULT_MODEL),
                        temperature=0.7,
                        max_tokens=2048,
                        timeout=ol_timeout
                    )
                    
                    reply = chat_completion.choices[0].message.content
                    logger.info(f"Groq reply received ({len(reply)} chars, model={payload.get('model', DEFAULT_MODEL)})")
                    
                except Exception as e:
                    logger.error(f"Groq API error: {type(e).__name__}: {e}")
                    if "timeout" in str(e).lower():
                        return {"error": "timeout", "message": f"Model timed out after {ol_timeout}s.", "suggestions": ["enable_fast", "retry"]}
                    elif "rate_limit" in str(e).lower() or "429" in str(e):
                        return {"error": "Rate limit reached. Please wait a moment and try again."}
                    else:
                        return {"error": f"LLM API error: {str(e)[:100]}"}
                finally:
                    elapsed = _time.time() - start_time
                    logger.info('Groq API call took %.2fs (fast=%s, model=%s, prompt_len=%d)', elapsed, getattr(req, 'fast', False), payload.get('model'), len(payload.get('prompt','')))
            
            # optionally save the user's message as memory
            if req.save:
                user_memory.add_memory(req.message)

            # append session history: user message then assistant reply (if conversation_mode on)
            try:
                if getattr(req, 'conversation_mode', True) and getattr(req, 'session_id', None):
                    sid = req.session_id
                    lst = sessions.get(sid, [])
                    lst.append({'role': 'user', 'text': req.message})
                    lst.append({'role': 'assistant', 'text': reply})
                    # trim to last N messages
                    sessions[sid] = lst[-(SESSION_MAX*2):]
            except Exception:
                pass

            return {"reply": reply}
        except requests.exceptions.RequestException as e:     # Helpful error message if the local model/API isn't reachable
            logger.error(f"Chat endpoint request error: {e}")
            return {"error": f"Failed to connect to Ollama API: {str(e)}"}
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.exception('Error in /chat: %s', tb)
        try:
            with open(os.path.join(os.path.dirname(__file__), 'error.log'), 'a', encoding='utf-8') as f:
                f.write(tb + '\n')
        except Exception:
            logger.exception('Failed to write to error.log')
        return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(e)})


@app.post('/chat/stream')
async def chat_stream(req: ChatRequest):
    """Stream assistant replies using a chunked transfer (SSE-like) interface.
    This endpoint yields text chunks as they arrive from the upstream model.
    Clients should POST JSON and stream the response body to append partial replies.
    """
    try:
        prompt, payload, ol_timeout = _build_prompt_and_payload(req)
        payload['stream'] = True

        # When running in test mode, yield some fake chunks to allow unit tests to exercise streaming logic
        if os.environ.get('GREENIE_TEST_MODE') == '1':
            async def fake_stream():
                import asyncio
                yield "data: " + "Starting stream..." + "\n\n"
                await asyncio.sleep(0.01)
                yield "data: " + "first chunk" + "\n\n"
                await asyncio.sleep(0.01)
                yield "data: " + " second chunk" + "\n\n"
                # finally, append to session as completed reply
            # record last prompt for debug
            global last_prompt
            last_prompt = prompt
            async def wrapper():
                accumulated = ''
                async for part in fake_stream():
                    # strip leading 'data: ' for accumulation
                    accumulated += part.replace('data: ', '').replace('\n\n','')
                    yield part
                # append session history if requested
                try:
                    if getattr(req, 'conversation_mode', True) and getattr(req, 'session_id', None):
                        sid = req.session_id
                        lst = sessions.get(sid, [])
                        lst.append({'role': 'user', 'text': req.message})
                        lst.append({'role': 'assistant', 'text': accumulated})
                        sessions[sid] = lst[-(SESSION_MAX*2):]
                except Exception:
                    pass
            return StreamingResponse(wrapper(), media_type='text/event-stream')

        # otherwise, use Groq streaming API
        def iter_stream():
            accumulated = ''
            try:
                if not groq_client:
                    yield f"event:error\ndata: LLM service not configured\n\n"
                    return
                
                # Use Groq streaming
                stream = groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are Greenie, a helpful IT support assistant."
                        },
                        {
                            "role": "user",
                            "content": payload["prompt"]
                        }
                    ],
                    model=payload.get('model', DEFAULT_MODEL),
                    temperature=0.7,
                    max_tokens=2048,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        yield f"data: {text}\n\n"
                        accumulated += text
                
                # after stream completes, append to session history if needed
                try:
                    if getattr(req, 'conversation_mode', True) and getattr(req, 'session_id', None):
                        sid = req.session_id
                        lst = sessions.get(sid, [])
                        lst.append({'role': 'user', 'text': req.message})
                        lst.append({'role': 'assistant', 'text': accumulated})
                        sessions[sid] = lst[-(SESSION_MAX*2):]
                except Exception:
                    pass
            except Exception as e:
                logger.exception('Error while streaming response: %s', e)
                yield f"event:error\ndata: {str(e)}\n\n"
        # store last_prompt too
        last_prompt = prompt
        return StreamingResponse(iter_stream(), media_type='text/event-stream')
    except Exception as e:
        logger.exception('Error in /chat/stream: %s', e)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get('/topic')
async def get_topic_endpoint():
    try:
        from memory import get_topic
        return {"topic": get_topic()}
    except Exception:
        return {"topic": None}

@app.post('/session/clear')
async def clear_session(req: dict):
    sid = req.get('session_id') if req else None
    if not sid:
        return {"ok": False, "error": "session_id required"}
    sessions.pop(sid, None)
    return {"ok": True}

@app.get('/session/{sid}')
async def get_session(sid: str):
    return {"session": sessions.get(sid, [])}


@app.post('/topic')
async def set_topic_endpoint(req: TopicRequest):
    try:
        from memory import set_topic, clear_topic
        if req.topic is None:
            clear_topic()
            return {"ok": True, "topic": None}
        set_topic(req.topic)
        return {"ok": True, "topic": req.topic}
    except Exception as e:
        return {"error": str(e)}


@app.get('/welcome')
async def welcome():
    try:
        try:
            from memory import get_topic
            topic = get_topic()
        except Exception:
            topic = None
        msg = "Hello! I'm Greenie, an AI assistant — witty, intelligent, and supportive. I'm aware my name is Greenie and I'm ready to chat."
        if topic:
            msg = msg + f" Current topic: {topic}."
        return {"message": msg}
    except Exception as e:
        logger.exception('Error in /welcome: %s', e)
        return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(e)})


@app.get('/debug/errors')
async def debug_errors(n: int = 50):
    """Return the last `n` lines of error.log for debugging (safe read)."""
    try:
        p = os.path.join(os.path.dirname(__file__), 'error.log')
        if not os.path.exists(p):
            return {"errors": []}
        with open(p, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        return {"errors": lines[-n:]}
    except Exception as e:
        logger.exception('Error in /debug/errors: %s', e)
        return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(e)})


@app.get('/tools/get_time')
async def tools_get_time():
    try:
        t = get_time()
        return {"ok": True, "time": t}
    except Exception as e:
        logger.exception('Error in /tools/get_time: %s', e)
        return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(e)})


@app.post('/log_uncertainty')
async def log_uncertainty(req: UncertaintyLogRequest):
    """Log when Greenie is uncertain so user can review and train."""
    try:
        log_path = os.path.join(os.path.dirname(__file__), 'uncertainty.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps({'user_message': req.user_message, 'reply': req.reply, 'ts': req.ts}) + '\n')
        return {"ok": True}
    except Exception as e:
        logger.exception('Error in /log_uncertainty: %s', e)
        return {"ok": False, "error": str(e)}


@app.get('/uncertainty/recent')
async def get_recent_uncertainty(n: int = 20):
    """Return recent uncertainty logs for review."""
    try:
        log_path = os.path.join(os.path.dirname(__file__), 'uncertainty.log')
        if not os.path.exists(log_path):
            return {"logs": []}
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        import json
        logs = [json.loads(line) for line in lines[-n:] if line.strip()]
        return {"logs": logs}
    except Exception as e:
        logger.exception('Error in /uncertainty/recent: %s', e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post('/tools/update')
async def tools_update(req: UpdateRequest, request: Request):
    # restrict to local callers for safety
    client_host = request.client.host if request.client else None
    allowed_hosts = ("127.0.0.1", "::1", "localhost", "testclient")
    if client_host not in allowed_hosts and client_host is not None:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    # best-effort git update
    result = _perform_git_update(req.branch if req and req.branch else None)
    return result


@app.get('/admin/update')
async def admin_get_update(request: Request):
    client_host = request.client.host if request.client else None
    allowed_hosts = ("127.0.0.1", "::1", "localhost", "testclient")
    if client_host not in allowed_hosts and client_host is not None:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    try:
        p = os.path.join(os.path.dirname(__file__), 'app.py')
        version = os.path.getmtime(p)
    except Exception:
        version = None
    return {"last_update": last_update or {}, "version": version}


@app.post('/admin/update')
async def admin_post_update(req: UpdateRequest, request: Request):
    client_host = request.client.host if request.client else None
    allowed_hosts = ("127.0.0.1", "::1", "localhost", "testclient")
    if client_host not in allowed_hosts and client_host is not None:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    if not req or not getattr(req, 'confirm', False):
        return JSONResponse(status_code=400, content={"error": "Confirmation required. Set 'confirm': true."})
    res = _perform_git_update(req.branch if req and req.branch else None)
    return res


@app.post('/admin/restart')
async def admin_restart(request: Request):
    client_host = request.client.host if request.client else None
    allowed_hosts = ("127.0.0.1", "::1", "localhost", "testclient")
    if client_host not in allowed_hosts and client_host is not None:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    # If shutdown hook exists, trigger it; otherwise return message indicating restart not performed
    if shutdown_hook:
        try:
            threading.Thread(target=shutdown_hook, daemon=True).start()
            return {"ok": True, "message": "Shutdown hook invoked"}
        except Exception as e:
            logger.exception('Admin restart failed: %s', e)
            return JSONResponse(status_code=500, content={"error": str(e)})
    return {"ok": False, "summary": "No shutdown hook installed; cannot restart from admin endpoint."}


# helper used by chat and /tools/update
def _perform_git_update(branch: str | None = None) -> dict:
    """Attempt to run 'git pull' in the project directory and then restart the process.
    Returns a dict with summary/stdout/stderr/updated boolean.
    This is intentionally best-effort and safe: if `.git` is not present or git is not available,
    it returns a descriptive message instead of raising.
    """
    repo_dir = os.path.dirname(__file__)
    git_dir = os.path.join(repo_dir, '.git')
    global last_update
    if not os.path.exists(git_dir):
        last_update = {"ts": time.time(), "ok": False, "summary": "No .git directory; cannot perform git pull in packaged app."}
        return {"ok": False, "summary": "No .git directory; cannot perform git pull in packaged app."}
    try:
        proc = subprocess.run(['git', 'pull', '--rebase'], cwd=repo_dir, capture_output=True, text=True, timeout=120)
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        updated = (proc.returncode == 0 and 'Already up to date.' not in stdout)
        summary = stdout.splitlines()[-1] if stdout else (stderr.splitlines()[-1] if stderr else '')
        result = {"ok": True, "updated": updated, "stdout": stdout, "stderr": stderr, "summary": summary}
        # record last_update for admin UI
        last_update = {"ts": time.time(), **result}
        # Try to restart gracefully if update happened
        if updated:
            try:
                # If an in-process shutdown hook is available, call it to gracefully stop the server
                if shutdown_hook:
                    threading.Thread(target=shutdown_hook, daemon=True).start()
                else:
                    # fallback: exit after a brief delay so a supervisor/runner can restart
                    threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True).start()
            except Exception:
                pass
        return result
    except Exception as e:
        res = {"ok": False, "summary": f"Exception when trying git pull: {e}"}
        try:
            last_update = {"ts": time.time(), **res}
        except Exception:
            pass
        return res


if __name__ == "__main__":
    # start uvicorn when launching the script/exe directly so double-clicking runs the server
    try:
        import uvicorn
        print("Starting Greenie HTTP server on http://127.0.0.1:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        # helpful diagnostics when double-clicked — print traceback and pause so the window stays open
        import traceback
        traceback.print_exc()
        try:
            print("Failed to start server. Ensure 'uvicorn' is installed: pip install uvicorn[standard]")
            input("Press Enter to exit...")
        except Exception:
            pass