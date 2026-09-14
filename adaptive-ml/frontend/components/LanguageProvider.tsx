"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  DEFAULT_LOCALE,
  loadLocale,
  persistLocale,
  translate,
} from "@/i18n";
import type { Locale, TranslationParams } from "@/i18n";

interface LanguageContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: TranslationParams) => string;
}

const LanguageContext =
  createContext<LanguageContextValue | null>(null);

function browserStore() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function LanguageProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(
    DEFAULT_LOCALE,
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let ignore = false;
    const loaded = loadLocale(browserStore());

    void Promise.resolve().then(() => {
      if (ignore) {
        return;
      }

      setLocaleState(loaded);
      setReady(true);
    });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }

    persistLocale(browserStore(), locale);
    document.documentElement.lang = locale;
  }, [locale, ready]);

  const value = useMemo(
    () => ({
      locale,
      setLocale(next: Locale) {
        setLocaleState(next);
      },
      t(key: string, params?: TranslationParams) {
        return translate(locale, key, params);
      },
    }),
    [locale],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const value = useContext(LanguageContext);

  if (!value) {
    throw new Error(
      "useLanguage must be used inside LanguageProvider.",
    );
  }

  return value;
}
