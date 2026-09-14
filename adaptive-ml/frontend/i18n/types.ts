export type Locale = "en" | "bg";

export interface TranslationParams {
  [key: string]: string | number;
}

export interface LocaleStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}
