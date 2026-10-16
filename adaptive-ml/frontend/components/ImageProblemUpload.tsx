"use client";

import { useEffect, useRef, useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import {
  extractProblemFromImage,
  getImageExtractionStatus,
} from "@/lib/api";
import {
  assignPreviewUrl,
  buildConfirmedImageProblem,
  canConfirmExtraction,
  confidenceCopyKey,
  fileIssueCopyKey,
  formatDiagramFact,
  formatFileSize,
  isBlockingUnreadable,
  languageCopyKey,
  mapImageUploadError,
  revokePreviewUrl,
  shouldApplyExtraction,
  validateImageFile,
  warningCopyKey,
} from "@/lib/imageProblem";
import type {
  ConfirmedImageProblem,
  ExtractedProblem,
} from "@/types/imageProblem";

export function ImageProblemUpload() {
  const { locale, t } = useLanguage();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const previewUrlRef = useRef<string | null>(null);
  const requestIdRef = useRef(0);
  const startedForFileRef = useRef<File | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const selectedFileRef = useRef<File | null>(null);

  const [availability, setAvailability] = useState<
    "checking" | "available" | "unavailable"
  >("checking");
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<
    string | null
  >(null);
  const [extraction, setExtraction] =
    useState<ExtractedProblem | null>(null);
  const [transcription, setTranscription] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [confirmed, setConfirmed] =
    useState<ConfirmedImageProblem | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let ignore = false;

    async function loadStatus() {
      try {
        const status = await getImageExtractionStatus();
        if (ignore) {
          return;
        }
        setAvailability(
          status.available ? "available" : "unavailable",
        );
      } catch {
        if (!ignore) {
          setAvailability("unavailable");
        }
      }
    }

    void loadStatus();

    return () => {
      ignore = true;
      abortRef.current?.abort();
      revokePreviewUrl(previewUrlRef.current);
      previewUrlRef.current = null;
    };
  }, []);

  function resetInputValue() {
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function clearWorkflow() {
    abortRef.current?.abort();
    abortRef.current = null;
    requestIdRef.current += 1;
    startedForFileRef.current = null;
    selectedFileRef.current = null;
    revokePreviewUrl(previewUrlRef.current);
    previewUrlRef.current = null;
    setPreviewUrl(null);
    setSelectedFile(null);
    setExtraction(null);
    setTranscription("");
    setAnalyzing(false);
    setConfirmed(null);
    setErrorKey(null);
    resetInputValue();
  }

  function handleFileList(files: FileList | null) {
    const file = files?.[0];
    if (!file) {
      return;
    }

    const issue = validateImageFile(file);
    if (issue !== "ok") {
      setErrorKey(fileIssueCopyKey(issue));
      resetInputValue();
      return;
    }

    abortRef.current?.abort();
    abortRef.current = null;
    requestIdRef.current += 1;
    startedForFileRef.current = null;
    const nextUrl = assignPreviewUrl(
      previewUrlRef.current,
      file,
    );
    previewUrlRef.current = nextUrl;
    selectedFileRef.current = file;
    setPreviewUrl(nextUrl);
    setSelectedFile(file);
    setExtraction(null);
    setTranscription("");
    setAnalyzing(false);
    setConfirmed(null);
    setErrorKey(null);
    resetInputValue();
  }

  async function handleAnalyze() {
    if (
      availability !== "available" ||
      !selectedFile ||
      analyzing
    ) {
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    startedForFileRef.current = selectedFile;
    setAnalyzing(true);
    setErrorKey(null);
    setConfirmed(null);

    try {
      const result = await extractProblemFromImage(
        selectedFile,
        locale,
        { signal: controller.signal },
      );
      if (
        !shouldApplyExtraction(
          requestIdRef.current,
          requestId,
          selectedFileRef.current,
          startedForFileRef.current,
        )
      ) {
        return;
      }
      setExtraction(result);
      setTranscription(result.transcription);
    } catch (error) {
      if (
        !shouldApplyExtraction(
          requestIdRef.current,
          requestId,
          selectedFileRef.current,
          startedForFileRef.current,
        )
      ) {
        return;
      }
      const mapped = mapImageUploadError(error);
      if (mapped) {
        setErrorKey(mapped);
      }
    } finally {
      if (requestIdRef.current === requestId) {
        setAnalyzing(false);
      }
    }
  }

  function handleConfirm() {
    if (
      !extraction ||
      confirmed ||
      !canConfirmExtraction(
        extraction,
        transcription,
        analyzing,
      )
    ) {
      return;
    }

    setConfirmed(
      buildConfirmedImageProblem(
        extraction,
        transcription,
      ),
    );
  }

  const available = availability === "available";
  const blocking =
    extraction !== null &&
    (extraction.multiple_problems_detected ||
      isBlockingUnreadable(extraction));
  const confirmEnabled = canConfirmExtraction(
    extraction,
    transcription,
    analyzing,
  );
  const showReview =
    extraction !== null && confirmed === null;
  const uniqueWarnings = extraction
    ? [...new Set(extraction.warnings)]
    : [];

  return (
    <section
      aria-labelledby="image-problem-upload-title"
      className="image-problem-upload"
    >
      <div className="image-problem-upload-inner">
        <h2 id="image-problem-upload-title">
          {t("imageUpload.title")}
        </h2>
        <p>{t("imageUpload.description")}</p>

        {availability === "unavailable" ? (
          <p
            className="image-problem-upload-unavailable"
            role="status"
          >
            {t("imageUpload.unavailable")}
          </p>
        ) : null}

        {availability !== "unavailable" ? (
          <>
            <div className="image-problem-upload-actions">
              <label className="image-problem-upload-choose">
                <input
                  accept="image/jpeg,image/png"
                  aria-label={t("imageUpload.choose")}
                  className="image-problem-upload-input"
                  disabled={!available || analyzing}
                  onChange={(event) => {
                    handleFileList(event.target.files);
                  }}
                  ref={inputRef}
                  type="file"
                />
                <span>
                  {selectedFile
                    ? t("imageUpload.replace")
                    : t("imageUpload.choose")}
                </span>
              </label>
              {selectedFile ? (
                <button
                  className="secondary-button"
                  onClick={clearWorkflow}
                  type="button"
                >
                  {t("imageUpload.remove")}
                </button>
              ) : null}
              {selectedFile && available ? (
                <button
                  disabled={analyzing}
                  onClick={() => {
                    void handleAnalyze();
                  }}
                  type="button"
                >
                  {analyzing
                    ? t("imageUpload.analyzing")
                    : t("imageUpload.analyze")}
                </button>
              ) : null}
            </div>
            <p className="image-problem-upload-supported">
              {t("imageUpload.supported")}
            </p>
          </>
        ) : null}

        {analyzing ? (
          <p
            aria-live="polite"
            className="image-problem-upload-status"
            role="status"
          >
            {t("imageUpload.analyzing")}
          </p>
        ) : null}

        {errorKey ? (
          <div className="image-problem-upload-error-row">
            <p className="error-message" role="alert">
              {t(errorKey)}
            </p>
            {selectedFile && available ? (
              <button
                className="secondary-button"
                disabled={analyzing}
                onClick={() => {
                  void handleAnalyze();
                }}
                type="button"
              >
                {t("imageUpload.tryAgain")}
              </button>
            ) : null}
          </div>
        ) : null}

        {previewUrl && selectedFile ? (
          <figure className="image-upload-preview">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              alt={t("imageUpload.previewAlt")}
              src={previewUrl}
            />
            <figcaption>
              {selectedFile.name} ·{" "}
              {formatFileSize(selectedFile.size)}
            </figcaption>
          </figure>
        ) : null}

        {showReview ? (
          <div className="image-upload-review">
            {extraction.multiple_problems_detected ? (
              <p
                className="image-upload-warning image-upload-warning-blocking"
                role="status"
              >
                {t("imageUpload.multipleProblems")}
              </p>
            ) : null}
            {isBlockingUnreadable(extraction) ? (
              <p
                className="image-upload-warning image-upload-warning-blocking"
                role="status"
              >
                {t("imageUpload.couldNotRead")}
              </p>
            ) : null}

            <label
              className="image-upload-transcription-label"
              htmlFor="image-upload-transcription"
            >
              {t("imageUpload.readAs")}
            </label>
            <textarea
              id="image-upload-transcription"
              onChange={(event) => {
                setTranscription(event.target.value);
              }}
              rows={6}
              value={transcription}
            />

            <dl className="image-upload-meta">
              <div>
                <dt>{t("imageUpload.detectedLanguage")}</dt>
                <dd>
                  {t(languageCopyKey(extraction.language))}
                </dd>
              </div>
              {confidenceCopyKey(extraction.confidence) ? (
                <div>
                  <dt>{t("imageUpload.confidence")}</dt>
                  <dd>
                    {t(
                      confidenceCopyKey(
                        extraction.confidence,
                      ) as string,
                    )}
                  </dd>
                </div>
              ) : null}
            </dl>

            {extraction.latex_expressions.length > 0 ? (
              <section className="image-upload-formulas">
                <h3>{t("imageUpload.detectedFormulas")}</h3>
                {extraction.latex_expressions.map(
                  (expression, index) => (
                    <MathContent
                      forceMath
                      key={`${expression}-${index}`}
                      text={expression}
                    />
                  ),
                )}
              </section>
            ) : null}

            {uniqueWarnings.length > 0 ? (
              <section>
                <h3>{t("imageUpload.warnings")}</h3>
                <ul className="image-upload-warning-list">
                  {uniqueWarnings.map((warning) => (
                    <li
                      className={warningClassName(warning)}
                      key={warning}
                    >
                      {t(warningCopyKey(warning))}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {extraction.ambiguities.length > 0 ? (
              <section className="image-upload-ambiguity">
                <h3>{t("imageUpload.ambiguities")}</h3>
                {extraction.ambiguities.map(
                  (item, index) => (
                    <div key={`${item.observation}-${index}`}>
                      <p>{t("imageUpload.checkThis")}</p>
                      <p>{item.observation}</p>
                      {item.candidates.length > 0 ? (
                        <p>
                          {t("imageUpload.possibleValues")}{" "}
                          {item.candidates.join(", ")}
                        </p>
                      ) : null}
                    </div>
                  ),
                )}
              </section>
            ) : null}

            {extraction.diagram_present ? (
              <section>
                <h3>{t("imageUpload.diagramDetected")}</h3>
                {extraction.diagram_type ? (
                  <p>{extraction.diagram_type}</p>
                ) : null}
                {extraction.diagram_facts.length > 0 ? (
                  <ul>
                    {extraction.diagram_facts.map(
                      (fact, index) => (
                        <li
                          key={`${fact.kind}-${fact.label}-${index}`}
                        >
                          {formatDiagramFact(fact)}
                        </li>
                      ),
                    )}
                  </ul>
                ) : null}
              </section>
            ) : null}

            {blocking && selectedFile ? (
              <button
                className="secondary-button"
                onClick={clearWorkflow}
                type="button"
              >
                {t("imageUpload.another")}
              </button>
            ) : null}

            {confirmEnabled ? (
              <button
                onClick={handleConfirm}
                type="button"
              >
                {t("imageUpload.looksCorrect")}
              </button>
            ) : null}
          </div>
        ) : null}

        {confirmed ? (
          <div className="image-upload-confirmed">
            <p role="status">
              {t("imageUpload.confirmed")}
            </p>
            <p>{t("imageUpload.confirmedNextStep")}</p>
            <div className="image-problem-upload-actions">
              <button
                className="secondary-button"
                onClick={() => {
                  setConfirmed(null);
                }}
                type="button"
              >
                {t("imageUpload.editAgain")}
              </button>
              <button
                className="secondary-button"
                onClick={clearWorkflow}
                type="button"
              >
                {t("imageUpload.another")}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function warningClassName(warning: string): string {
  if (
    warning === "unreadable" ||
    warning === "no_problem_found" ||
    warning === "multiple_problems_detected"
  ) {
    return "image-upload-warning image-upload-warning-blocking";
  }
  return "image-upload-warning";
}
