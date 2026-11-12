import { Show, UserButton } from '@clerk/react'
import { Dashboard } from './Dashboard'
import { Landing } from './Landing'

function App() {
  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">OOS Watch</h1>
        {/* The round account button, with "Manage account" and "Sign out" in its menu. */}
        <Show when="signed-in">
          <UserButton />
        </Show>
      </header>

      {/* Show draws its contents only when the condition holds, and nothing while Clerk is
          still working out whether anyone is signed in. */}
      <Show when="signed-out">
        <Landing />
      </Show>
      <Show when="signed-in">
        <Dashboard />
      </Show>
    </main>
  )
}

export default App
