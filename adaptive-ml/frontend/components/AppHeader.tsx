"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";

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
  const progressOpen =
    pathname === "/" && isProgressView(searchParams);
  const loginOpen = pathname === LOGIN_HREF;

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link className="brand-lockup" href={HOME_HREF}>
          <span className="brand-name">MAT-PAL</span>
          <span className="brand-subtitle">
            Math &amp; Physics Adaptive Learning
          </span>
        </Link>

        <nav aria-label="Primary" className="app-nav">
          <Link href={LEARN_HREF}>Learn</Link>
          <Link
            aria-current={progressOpen ? "page" : undefined}
            href={PROGRESS_HREF}
          >
            Progress
          </Link>
          <ProfileSelector />
          <Link
            aria-current={loginOpen ? "page" : undefined}
            href={LOGIN_HREF}
          >
            Log in
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
              <span className="brand-subtitle">
                Math &amp; Physics Adaptive Learning
              </span>
            </a>
            <nav aria-label="Primary" className="app-nav">
              <a href={LEARN_HREF}>Learn</a>
              <a href={PROGRESS_HREF}>Progress</a>
              <a href={LOGIN_HREF}>Log in</a>
            </nav>
          </div>
        </header>
      }
    >
      <HeaderNav />
    </Suspense>
  );
}
