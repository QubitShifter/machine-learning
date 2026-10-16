import type {
  ConfirmedImageProblem,
  ExtractedDiagramFact,
  ExtractedProblem,
} from "@/types/imageProblem";
import { MatPalApiError } from "./matPalApiError.ts";

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

export const ALLOWED_IMAGE_MIME_TYPES = [
  "image/jpeg",
  "image/png",
] as const;

const BLOCKING_WARNINGS = new Set([
  "unreadable",
  "no_problem_found",
]);

const WARNING_COPY_KEYS: Record<string, string> = {
  unreadable: "imageUpload.unreadable",
  cropped: "imageUpload.cropped",
  multiple_problems_detected:
    "imageUpload.multipleProblems",
  handwriting_heavy: "imageUpload.handwritingHeavy",
  no_problem_found: "imageUpload.noProblem",
  low_contrast: "imageUpload.lowContrast",
};

export type ImageFileIssue =
  | "ok"
  | "empty"
  | "unsupported"
  | "too_large";

export function validateImageFile(
  file: File,
): ImageFileIssue {
  if (file.size <= 0) {
    return "empty";
  }

  if (file.size > MAX_IMAGE_BYTES) {
    return "too_large";
  }

  const mime = normalizeFileMime(file);
  if (
    mime !== "image/jpeg" &&
    mime !== "image/png"
  ) {
    return "unsupported";
  }

  return "ok";
}

export function normalizeFileMime(file: File): string {
  const mime = file.type.trim().toLowerCase();
  if (mime === "image/jpeg" || mime === "image/png") {
    return mime;
  }

  const name = file.name.trim().toLowerCase();
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  if (name.endsWith(".png")) {
    return "image/png";
  }

  return mime;
}

export function fileIssueCopyKey(
  issue: Exclude<ImageFileIssue, "ok">,
): string {
  if (issue === "too_large") {
    return "imageUpload.tooLarge";
  }
  if (issue === "empty") {
    return "imageUpload.empty";
  }
  return "imageUpload.unsupportedType";
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    if (kilobytes < 10) {
      return `${kilobytes.toFixed(1)} KB`;
    }
    return `${Math.round(kilobytes)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isBlockingUnreadable(
  extraction: ExtractedProblem,
): boolean {
  return extraction.warnings.some((warning) =>
    BLOCKING_WARNINGS.has(warning),
  );
}

export function canConfirmExtraction(
  extraction: ExtractedProblem | null,
  transcription: string,
  analyzing: boolean,
): boolean {
  if (!extraction || analyzing) {
    return false;
  }

  if (!transcription.trim()) {
    return false;
  }

  if (extraction.multiple_problems_detected) {
    return false;
  }

  if (isBlockingUnreadable(extraction)) {
    return false;
  }

  return true;
}

export function warningCopyKey(warning: string): string {
  return (
    WARNING_COPY_KEYS[warning] ??
    "imageUpload.genericWarning"
  );
}

export function languageCopyKey(
  language: ExtractedProblem["language"],
): string {
  return `imageUpload.language.${language}`;
}

export function confidenceCopyKey(
  confidence: ExtractedProblem["confidence"],
): string | null {
  if (!confidence) {
    return null;
  }
  if (confidence === "low") {
    return "imageUpload.confidenceLow";
  }
  if (confidence === "medium") {
    return "imageUpload.confidenceMedium";
  }
  return "imageUpload.confidenceHigh";
}

export function formatDiagramFact(
  fact: ExtractedDiagramFact,
): string {
  const unit = fact.unit ? ` ${fact.unit}` : "";
  if (fact.label && fact.value) {
    return `${fact.label} = ${fact.value}${unit}`;
  }
  if (fact.label) {
    return fact.label;
  }
  if (fact.value) {
    return `${fact.value}${unit}`;
  }
  return fact.kind;
}

export function buildConfirmedImageProblem(
  extraction: ExtractedProblem,
  transcription: string,
): ConfirmedImageProblem {
  return {
    transcription: transcription.trim(),
    language: extraction.language,
    latexExpressions: extraction.latex_expressions,
    topicHint: extraction.topic_hint,
    problemTypeHint: extraction.problem_type_hint,
  };
}

export function shouldApplyExtraction(
  currentRequestId: number,
  responseRequestId: number,
  selectedFile: File | null,
  startedForFile: File | null,
): boolean {
  return (
    currentRequestId === responseRequestId &&
    selectedFile !== null &&
    selectedFile === startedForFile
  );
}

export function assignPreviewUrl(
  previousUrl: string | null,
  file: File,
  io: {
    create: (nextFile: File) => string;
    revoke: (url: string) => void;
  } = {
    create: (nextFile) => URL.createObjectURL(nextFile),
    revoke: (url) => {
      URL.revokeObjectURL(url);
    },
  },
): string {
  if (previousUrl) {
    io.revoke(previousUrl);
  }
  return io.create(file);
}

export function revokePreviewUrl(
  url: string | null,
  revoke: (value: string) => void = (value) => {
    URL.revokeObjectURL(value);
  },
): void {
  if (url) {
    revoke(url);
  }
}

export function mapImageUploadError(
  error: unknown,
): string | null {
  if (isAbortError(error)) {
    return null;
  }

  if (error instanceof MatPalApiError) {
    if (error.status === 400) {
      const detail = error.message.toLowerCase();
      if (
        detail.includes("5 mib") ||
        detail.includes("too large") ||
        detail.includes("exceeds")
      ) {
        return "imageUpload.tooLarge";
      }
      if (detail.includes("empty")) {
        return "imageUpload.empty";
      }
      if (
        detail.includes("unsupported") ||
        detail.includes("image type")
      ) {
        return "imageUpload.unsupportedType";
      }
      return "imageUpload.invalidImage";
    }
    if (error.status === 422) {
      return "imageUpload.parseError";
    }
    if (error.status === 503) {
      return "imageUpload.unavailable";
    }
    if (error.status === 504) {
      return "imageUpload.timeout";
    }
  }

  if (error instanceof TypeError) {
    return "imageUpload.networkError";
  }

  return "imageUpload.genericError";
}

export function imageExtractionStatusPath(): string {
  return "/problems/from-image/status";
}

export function buildImageExtractRequest(
  file: File,
  localeHint?: string,
  apiBaseUrl = "http://localhost:8000",
): { url: string; init: RequestInit } {
  const formData = new FormData();
  formData.append("file", file);
  const query = localeHint
    ? `?locale_hint=${encodeURIComponent(localeHint)}`
    : "";

  return {
    url: `${apiBaseUrl}/problems/from-image${query}`,
    init: {
      method: "POST",
      body: formData,
    },
  };
}

export function isAbortError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error as { name?: string }).name === "AbortError"
  );
}
