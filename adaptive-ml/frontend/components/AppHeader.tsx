"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ProfileSelector } from "@/components/ProfileSelector";
import {
  HOME_HREF,
  LEARN_HREF,
  LOGIN_HREF,
  PROGRESS_HREF,
  isProgressView,
} from "@/lib/learningPath";

function HeaderNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { t } = useLanguage();
  const progressOpen =
    pathname === "/" && isProgressView(searchParams);
  const loginOpen = pathname === LOGIN_HREF;

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link className="brand-lockup" href={HOME_HREF}>
          <span className="brand-name">MAT-PAL</span>
          <span className="brand-subtitle">
            {t("brand.subtitle")}
          </span>
        </Link>

        <div className="app-header-controls">
          <ProfileSelector />
          <LanguageSwitcher />
        </div>

        <nav aria-label={t("nav.primary")} className="app-nav">
          <Link href={LEARN_HREF}>{t("nav.learn")}</Link>
          <Link
            aria-current={progressOpen ? "page" : undefined}
            href={PROGRESS_HREF}
          >
            {t("nav.progress")}
          </Link>
          <Link
            aria-current={loginOpen ? "page" : undefined}
            href={LOGIN_HREF}
          >
            {t("nav.login")}
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function AppHeader() {
  return (
    <Suspense
      fallback={
        <header className="app-header">
          <div className="app-header-inner">
            <a className="brand-lockup" href={HOME_HREF}>
              <span className="brand-name">MAT-PAL</span>
            </a>
          </div>
        </header>
      }
    >
      <HeaderNav />
    </Suspense>
  );
}
