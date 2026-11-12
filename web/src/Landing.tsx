import { SignInButton, SignUpButton } from '@clerk/react'

/** What a visitor sees before signing in. */
export function Landing() {
  return (
    <section className="py-12">
      <h2 className="text-3xl font-semibold">Know your safety record before FMCSA calls.</h2>
      <p className="mt-3 max-w-2xl text-ink-secondary">
        OOS Watch turns your carrier&rsquo;s public FMCSA inspection, violation and crash records into one dashboard:
        out-of-service rates against the national average, trends by month, and the records worth challenging.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        {/* Clerk's buttons open its sign-up and sign-in boxes over the page. We only supply the look. */}
        <SignUpButton mode="modal">
          <button className="rounded-md bg-ink px-4 py-2 font-medium text-page">Sign up</button>
        </SignUpButton>
        <SignInButton mode="modal">
          <button className="rounded-md border border-border px-4 py-2 font-medium hover:bg-surface">Log in</button>
        </SignInButton>
      </div>
    </section>
  )
}
