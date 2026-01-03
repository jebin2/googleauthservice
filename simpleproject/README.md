# Simple Project - Google Auth Demo

A complete demo showing how to use google-auth-service library from GitHub.

---

## Prerequisites

1. **Google Cloud Console** - Create OAuth 2.0 credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select a project
   - Go to **APIs & Services → Credentials**
   - Create **OAuth 2.0 Client ID** (Web application)
   - Add authorized origins: `http://localhost:3000`, `http://localhost:5173`
   - Copy the **Client ID**

---

## Step 1: Configure Environment

```bash
cd simpleproject
cp .env.example .env
```

Edit `.env` with your values:
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
JWT_SECRET=<generate-with-command-below>
```

**Generate a secure JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output and paste it as `JWT_SECRET` value.

---

## Step 2: Run Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies (includes google-auth-service from GitHub)
pip install -r requirements.txt

# Run server
python main.py
```

Backend runs at: **http://localhost:8000**

Test it:
```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

---

## Step 3: Run Frontend

```bash
cd frontend

# Install dependencies (includes @jebin2/googleauthservice from GitHub)
npm install

# Update Google Client ID in .env or directly in src/App.tsx
# Look for: VITE_GOOGLE_CLIENT_ID

# Run dev server
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## Step 4: Test the Flow

1. Open http://localhost:5173 in browser
2. Click **"Sign in with Google"**
3. Authenticate with your Google account
4. Click **"Test Protected API"** to call a protected endpoint
5. Click **"Sign Out"** to logout

---

## API Endpoints (Backend)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Health check |
| `/health` | GET | No | Health check |
| `/auth/google` | POST | No | Exchange Google ID token for JWT |
| `/auth/me` | GET | Yes | Get current user info |
| `/auth/logout` | POST | Yes | Logout (invalidate tokens) |
| `/api/protected` | GET | Yes | Example protected endpoint |

---

## Project Structure

```
simpleproject/
├── .env.example          # Environment template
├── backend/
│   ├── requirements.txt  # Python deps (installs from GitHub)
│   └── main.py           # FastAPI server
└── frontend/
    ├── package.json      # Node deps (installs from GitHub)
    └── src/
        └── App.tsx       # React app using the library
```

---

## How It Works

**Backend** installs via pip:
```
google-auth-service @ git+https://github.com/jebin2/googleauthservice.git@main#subdirectory=server
```

**Frontend** installs via npm:
```json
"@jebin2/googleauthservice": "git+https://github.com/jebin2/googleauthservice.git"
```

Both install directly from GitHub - no npm/PyPI publishing needed!
