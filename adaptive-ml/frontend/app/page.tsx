import { Suspense } from "react";

import { HomePage } from "@/components/HomePage";

export default function Home() {
  return (
    <Suspense
      fallback={
        <main className="page-shell">
          <p>Loading MAT-PAL…</p>
        </main>
      }
    >
      <HomePage />
    </Suspense>
  );
}
