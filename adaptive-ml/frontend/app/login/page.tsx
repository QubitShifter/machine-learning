"use client";

import Link from "next/link";

import { useLanguage } from "@/components/LanguageProvider";
import { HOME_HREF } from "@/lib/learningPath";

export default function LoginPage() {
  const { t } = useLanguage();

  return (
    <main className="page-shell">
      <section className="login-card">
        <p className="eyebrow">{t("login.eyebrow")}</p>
        <h1>{t("login.title")}</h1>
        <p>{t("login.intro")}</p>
        <p className="login-message" role="status">
          {t("login.notImplemented")}
        </p>

        <form
          className="login-form"
          onSubmit={(event) => event.preventDefault()}
        >
          <label>
            {t("login.email")}
            <input
              autoComplete="username"
              disabled
              name="email"
              placeholder="you@example.com"
              type="email"
            />
          </label>
          <label>
            {t("login.password")}
            <input
              autoComplete="current-password"
              disabled
              name="password"
              placeholder={t("login.password")}
              type="password"
            />
          </label>
          <button disabled type="submit">
            {t("login.submit")}
          </button>
        </form>

        <p className="login-alt">
          {t("login.noAccount")}{" "}
          <span className="login-coming-soon">
            {t("login.signUpSoon")}
          </span>
        </p>

        <Link
          className="secondary-button login-local-link"
          href={HOME_HREF}
        >
          {t("login.continueGuest")}
        </Link>
      </section>
    </main>
  );
}
