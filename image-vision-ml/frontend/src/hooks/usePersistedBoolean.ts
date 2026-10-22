import { useEffect, useState } from "react";

export function usePersistedBoolean(key: string, initial: boolean): [boolean, (value: boolean | ((current: boolean) => boolean)) => void] {
  const [value, setValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem(key);
      if (stored === "1") return true;
      if (stored === "0") return false;
    } catch {
      // Private mode may block sessionStorage.
    }
    return initial;
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(key, value ? "1" : "0");
    } catch {
      // Ignore persistence failures.
    }
  }, [key, value]);

  return [value, setValue];
}
