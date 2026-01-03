# Google Auth Service

A reusable, plug-and-play Google Sign-In library for web projects.

## Overview

This library provides both **client** (TypeScript/React) and **server** (Python/FastAPI) modules for implementing Google Sign-In authentication in any web application.

## Features

### Client Module (`/client`)
- Google Identity Services integration
- JWT token refresh with automatic retry
- Multi-storage fallback (localStorage → cookies → IndexedDB)
- Customizable sign-in button component
- User avatar component with caching

### Server Module (`/server`)
- Google ID token verification
- JWT access/refresh token management
- FastAPI middleware (database-agnostic)
- Flexible route-based auth configuration

## Quick Start

### Client
```bash
cd client
npm install
# Copy src/ to your project
```

### Server
```bash
cd server
pip install -r requirements.txt
# Copy src/google_auth_service to your project
```

## Documentation

- [Client Integration Guide](client/CLIENT-LINK.md)
- [Server Integration Guide](server/SERVER-LINK.md)
- [Quick Start](docs/QUICK-START.md)

## Environment Variables

### Client
```
VITE_GOOGLE_CLIENT_ID=your-google-client-id
VITE_API_BASE_URL=https://api.yoursite.com
```

### Server
```
AUTH_SIGN_IN_GOOGLE_CLIENT_ID=your-google-client-id
JWT_SECRET=your-secret-key-min-32-chars
```

## License

MIT
