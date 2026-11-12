import { ClerkProvider } from '@clerk/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Vite copies variables that start with VITE_ from web/.env.local into the page.
const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
if (!publishableKey) {
  throw new Error('VITE_CLERK_PUBLISHABLE_KEY is not set (see web/.env.local)')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* ClerkProvider makes "who is signed in" available to every component inside it. */}
    <ClerkProvider publishableKey={publishableKey}>
      <App />
    </ClerkProvider>
  </StrictMode>,
)
