import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

import { GoogleAuthProvider } from '@jebin2/googleauthservice/client/src'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GoogleAuthProvider
      clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID'}
      apiBaseUrl={import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
    >
      <App />
    </GoogleAuthProvider>
  </React.StrictMode>,
)
