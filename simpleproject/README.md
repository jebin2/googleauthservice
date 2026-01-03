# Simple Project - Google Auth Demo

A minimal demo application showing how to integrate google-auth-service.

## Quick Start

### 1. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your Google Client ID and JWT secret
```

### 2. Run Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Run Frontend
```bash
cd frontend
# Open index.html in browser, or serve with:
python -m http.server 3000
```

### 4. Test
- Open http://localhost:3000
- Click "Sign in with Google"
- See authenticated user info

## Files
- `backend/main.py` - FastAPI app with Google auth endpoints
- `frontend/index.html` - Simple HTML/JS demo page
