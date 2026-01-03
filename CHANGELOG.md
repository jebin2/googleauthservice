# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-01-03

### Added
- **Client Package**
  - `GoogleAuthProvider` React context for app-wide auth state
  - `useGoogleAuth` hook for accessing auth state
  - `GoogleSignInButton` component (native Google and custom styles)
  - `UserAvatar` component with fallback support
  - `authenticatedFetch` for automatic token handling
  - Multi-tab session synchronization
  - Multi-storage strategy (localStorage + cookie + IndexedDB)

- **Server Package**
  - `GoogleAuth` class for FastAPI integration
  - `GoogleAuthMiddleware` for route protection  
  - `JWTService` for access and refresh tokens
  - `BaseUserStore` abstract class for database flexibility
  - `InMemoryUserStore` for development/testing
  - Token versioning for session revocation

- **Documentation**
  - CLIENT-LINK.md integration guide
  - SERVER-LINK.md integration guide
  - simpleproject demo application

### Changed
- Standardized environment variable to `GOOGLE_CLIENT_ID` (with backward compatibility for `AUTH_SIGN_IN_GOOGLE_CLIENT_ID`)
- npm package renamed to `@jebin2/googleauthservice`

### Removed
- `credits` field from `GoogleUser` type (application-specific feature)
- `updateUserCredits` function (moved to consumer applications)

## Environment Variables

### Server
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
JWT_SECRET=your-secret-key
JWT_ACCESS_EXPIRY_MINUTES=15   # optional
JWT_REFRESH_EXPIRY_DAYS=7      # optional
```

### Client
```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=https://api.yoursite.com
```
