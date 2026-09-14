import { Suspense } from "react";

import { HomePage } from "@/components/HomePage";
import { PageLoadingFallback } from "@/components/PageLoadingFallback";

export default function Home() {
  return (
    <Suspense fallback={<PageLoadingFallback />}>
      <HomePage />
    </Suspense>
  );
}
