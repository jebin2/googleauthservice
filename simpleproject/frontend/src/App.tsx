import { useEffect, useState } from 'react'
import './App.css'

// Import from npm-installed google-auth-service
import {
  configureGoogleAuth,
  initializeAuth,
  onAuthStateChange,
  signOut,
  authenticatedFetch,
  GoogleSignInButton,
  UserAvatar,
  GoogleUser,
} from '@jebin2/googleauthservice/client/src'

// Configure Google Auth
configureGoogleAuth({
  clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

function App() {
  const [user, setUser] = useState<GoogleUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiResult, setApiResult] = useState<string | null>(null)

  useEffect(() => {
    // Subscribe to auth state changes
    const unsubscribe = onAuthStateChange(setUser)

    // Initialize (restores session from cookie)
    initializeAuth()
      .then(setUser)
      .finally(() => setLoading(false))

    return unsubscribe
  }, [])

  const handleTestApi = async () => {
    try {
      const response = await authenticatedFetch('http://localhost:8000/api/protected')
      const data = await response.json()
      setApiResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setApiResult(`Error: ${error}`)
    }
  }

  const handleSignOut = async () => {
    await signOut()
    setApiResult(null)
  }

  if (loading) {
    return <div className="container">Loading...</div>
  }

  return (
    <div className="container">
      <h1>🔐 Google Auth Demo</h1>
      <p className="subtitle">Testing google-auth-service npm package</p>

      {!user ? (
        <div className="login-section">
          <GoogleSignInButton width={300} />
        </div>
      ) : (
        <div className="user-section">
          <UserAvatar
            src={user.profilePicture}
            name={user.name}
            email={user.email}
            size="lg"
          />
          <h2>{user.name || 'User'}</h2>
          <p className="email">{user.email}</p>

          <div className="buttons">
            <button onClick={handleTestApi} className="btn-primary">
              Test Protected API
            </button>
            <button onClick={handleSignOut} className="btn-outline">
              Sign Out
            </button>
          </div>

          {apiResult && (
            <pre className="api-result">{apiResult}</pre>
          )}
        </div>
      )}
    </div>
  )
}

export default App
