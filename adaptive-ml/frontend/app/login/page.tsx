"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  AUTH_PLACEHOLDER_MESSAGE,
  HOME_HREF,
} from "@/lib/learningPath";

export default function LoginPage() {
  const [message, setMessage] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage(AUTH_PLACEHOLDER_MESSAGE);
  }

  return (
    <main className="page-shell">
      <section className="login-card">
        <p className="eyebrow">Account</p>
        <h1>Log in to MAT-PAL</h1>
        <p>
          Sign-in will arrive later. You can keep
          practicing as the local student.
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="username"
              name="email"
              placeholder="you@example.com"
              type="email"
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              name="password"
              placeholder="Password"
              type="password"
            />
          </label>
          <button type="submit">Log in</button>
        </form>

        <p className="login-alt">
          Don&apos;t have an account?{" "}
          <button
            className="text-button"
            onClick={() =>
              setMessage(AUTH_PLACEHOLDER_MESSAGE)
            }
            type="button"
          >
            Sign up
          </button>
        </p>

        <Link
          className="secondary-button login-local-link"
          href={HOME_HREF}
        >
          Continue as local student
        </Link>

        {message ? (
          <p className="login-message" role="status">
            {message}
          </p>
        ) : null}
      </section>
    </main>
  );
}
