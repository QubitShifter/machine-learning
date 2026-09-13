"use client";

import Link from "next/link";

import {
  AUTH_PLACEHOLDER_MESSAGE,
  HOME_HREF,
} from "@/lib/learningPath";

export default function LoginPage() {
  return (
    <main className="page-shell">
      <section className="login-card">
        <p className="eyebrow">Account</p>
        <h1>Log in to MAT-PAL</h1>
        <p>
          Local profiles work on this device.
          Account login will be added later.
        </p>
        <p className="login-message" role="status">
          {AUTH_PLACEHOLDER_MESSAGE}
        </p>

        <form
          className="login-form"
          onSubmit={(event) => event.preventDefault()}
        >
          <label>
            Email
            <input
              autoComplete="username"
              disabled
              name="email"
              placeholder="you@example.com"
              type="email"
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              disabled
              name="password"
              placeholder="Password"
              type="password"
            />
          </label>
          <button disabled type="submit">
            Log in
          </button>
        </form>

        <p className="login-alt">
          Don&apos;t have an account?{" "}
          <span className="login-coming-soon">
            Sign up — coming soon
          </span>
        </p>

        <Link
          className="secondary-button login-local-link"
          href={HOME_HREF}
        >
          Continue as Guest
        </Link>
      </section>
    </main>
  );
}
