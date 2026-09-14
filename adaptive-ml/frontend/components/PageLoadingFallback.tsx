"use client";

import { useLanguage } from "@/components/LanguageProvider";

export function PageLoadingFallback() {
  const { t } = useLanguage();

  return (
    <main className="page-shell">
      <p>{t("path.loading")}</p>
    </main>
  );
}
