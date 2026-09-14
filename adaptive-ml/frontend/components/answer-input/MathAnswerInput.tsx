"use client";

import { useEffect, useRef, useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import type { AnswerEditorProps } from "@/components/answer-input/types";

type MathfieldElement = HTMLElement & {
  value: string;
  disabled?: boolean;
};

export function MathAnswerInput({
  value,
  expectedInputType,
  disabled,
  onChange,
  onSubmit,
}: AnswerEditorProps) {
  const { t } = useLanguage();
  const containerRef = useRef<HTMLDivElement | null>(
    null,
  );
  const mathfieldRef =
    useRef<MathfieldElement | null>(null);
  const onChangeRef = useRef(onChange);
  const valueRef = useRef(value);
  const disabledRef = useRef(disabled);
  const [editorReady, setEditorReady] =
    useState(false);
  const [loadError, setLoadError] = useState<
    string | null
  >(null);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    valueRef.current = value;

    if (
      mathfieldRef.current &&
      mathfieldRef.current.value !== value
    ) {
      mathfieldRef.current.value = value;
    }
  }, [value]);

  useEffect(() => {
    disabledRef.current = disabled;

    if (mathfieldRef.current) {
      mathfieldRef.current.disabled = disabled;
    }
  }, [disabled]);

  useEffect(() => {
    let disposed = false;
    let mathfield: MathfieldElement | null = null;
    let mountedContainer: HTMLDivElement | null =
      null;

    async function mountMathfield() {
      try {
        await import("mathlive");

        if (
          disposed ||
          containerRef.current === null
        ) {
          return;
        }

        mountedContainer = containerRef.current;
        mathfield = document.createElement(
          "math-field",
        ) as MathfieldElement;
        mathfield.value = valueRef.current;
        mathfield.disabled = disabledRef.current;
        mathfield.setAttribute(
          "aria-label",
          "Mathematical answer",
        );
        mathfield.setAttribute(
          "virtual-keyboard-mode",
          "manual",
        );

        mathfield.addEventListener(
          "input",
          () => {
            onChangeRef.current(
              mathfield?.value ?? "",
            );
          },
        );

        mountedContainer.appendChild(
          mathfield,
        );
        mathfieldRef.current = mathfield;
        setEditorReady(true);
      } catch {
        setLoadError("mathlive");
      }
    }

    void mountMathfield();

    return () => {
      disposed = true;
      const container = mountedContainer;

      if (
        mathfield &&
        container &&
        mathfield.parentNode === container
      ) {
        container.removeChild(mathfield);
      }

      mathfieldRef.current = null;
    };
  }, []);

  useEffect(() => {
    mathfieldRef.current?.setAttribute(
      "aria-label",
      t("tutor.mathAria"),
    );
  }, [t]);

  return (
    <form
      className="answer-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="math-answer">
        {t("tutor.yourAnswer")}
      </label>
      <div
        className="math-answer-field"
        id="math-answer"
        ref={containerRef}
      />

      {!editorReady && !loadError ? (
        <p className="math-answer-loading">
          {t("tutor.mathLoading")}
        </p>
      ) : null}

      {loadError ? (
        <p className="error-message">
          {t("tutor.mathLoadError")}
        </p>
      ) : null}

      <div className="math-answer-actions">
        <button
          disabled={
            disabled ||
            !editorReady ||
            !value.trim()
          }
          type="submit"
        >
          {t("tutor.submit")}
        </button>
      </div>

      <p className="input-type-note">
        {t("tutor.expectedMath", { type: expectedInputType })}
      </p>
    </form>
  );
}
