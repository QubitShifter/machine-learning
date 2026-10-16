import { bg } from "../i18n/bg.ts";
import { en } from "../i18n/en.ts";
import { translate } from "../i18n/index.ts";
import {
  isMathOnlyLine,
} from "../components/math/mathContentClassification.ts";
import { MatPalApiError } from "./matPalApiError.ts";
import {
  assignPreviewUrl,
  buildConfirmedImageProblem,
  buildImageExtractRequest,
  canConfirmExtraction,
  confidenceCopyKey,
  fileIssueCopyKey,
  formatDiagramFact,
  formatFileSize,
  imageExtractionStatusPath,
  isBlockingUnreadable,
  mapImageUploadError,
  MAX_IMAGE_BYTES,
  revokePreviewUrl,
  shouldApplyExtraction,
  validateImageFile,
  warningCopyKey,
} from "./imageProblem.ts";
import type { ExtractedProblem } from "../types/imageProblem.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const IMAGE_UPLOAD_KEYS = [
  "imageUpload.title",
  "imageUpload.description",
  "imageUpload.choose",
  "imageUpload.supported",
  "imageUpload.replace",
  "imageUpload.remove",
  "imageUpload.analyze",
  "imageUpload.analyzing",
  "imageUpload.previewAlt",
  "imageUpload.unavailable",
  "imageUpload.readAs",
  "imageUpload.detectedLanguage",
  "imageUpload.detectedFormulas",
  "imageUpload.diagramDetected",
  "imageUpload.ambiguities",
  "imageUpload.checkThis",
  "imageUpload.possibleValues",
  "imageUpload.warnings",
  "imageUpload.looksCorrect",
  "imageUpload.editAgain",
  "imageUpload.confirmed",
  "imageUpload.confirmedNextStep",
  "imageUpload.another",
  "imageUpload.tryAgain",
  "imageUpload.tooLarge",
  "imageUpload.unsupportedType",
  "imageUpload.empty",
  "imageUpload.invalidImage",
  "imageUpload.unreadable",
  "imageUpload.couldNotRead",
  "imageUpload.cropped",
  "imageUpload.multipleProblems",
  "imageUpload.handwritingHeavy",
  "imageUpload.noProblem",
  "imageUpload.lowContrast",
  "imageUpload.genericWarning",
  "imageUpload.timeout",
  "imageUpload.parseError",
  "imageUpload.networkError",
  "imageUpload.genericError",
  "imageUpload.confidence",
  "imageUpload.confidenceLow",
  "imageUpload.confidenceMedium",
  "imageUpload.confidenceHigh",
  "imageUpload.language.en",
  "imageUpload.language.bg",
  "imageUpload.language.unknown",
] as const;

function makeFile(
  name: string,
  type: string,
  size: number,
): File {
  const bytes = size > 0 ? new Uint8Array(size) : new Uint8Array();
  if (type === "image/png" && size >= 8) {
    bytes.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  }
  if (type === "image/jpeg" && size >= 3) {
    bytes.set([0xff, 0xd8, 0xff]);
  }
  return new File([bytes], name, { type });
}

function sampleExtraction(
  overrides: Partial<ExtractedProblem> = {},
): ExtractedProblem {
  return {
    transcription: "2x + 5 = 17",
    language: "en",
    problem_type_hint: "equation",
    topic_hint: "arithmetic",
    latex_expressions: ["2x + 5 = 17"],
    diagram_present: false,
    diagram_type: null,
    diagram_facts: [],
    ambiguities: [],
    warnings: [],
    multiple_problems_detected: false,
    confidence: "high",
    source: {
      content_type: "image/png",
      byte_size: 128,
    },
    ...overrides,
  };
}

assert(
  validateImageFile(makeFile("problem.png", "image/png", 32)) ===
    "ok",
  "valid PNG must be accepted",
);
assert(
  validateImageFile(
    makeFile("problem.jpg", "image/jpeg", 32),
  ) === "ok",
  "valid JPEG must be accepted",
);
assert(
  validateImageFile(makeFile("notes.pdf", "application/pdf", 32)) ===
    "unsupported",
  "PDF must be rejected client-side",
);
assert(
  validateImageFile(makeFile("icon.svg", "image/svg+xml", 32)) ===
    "unsupported",
  "SVG must be rejected client-side",
);
assert(
  validateImageFile(makeFile("photo.webp", "image/webp", 32)) ===
    "unsupported",
  "WebP must be rejected client-side",
);
assert(
  validateImageFile(makeFile("empty.png", "image/png", 0)) ===
    "empty",
  "empty file must be rejected",
);
assert(
  validateImageFile(
    makeFile("huge.png", "image/png", MAX_IMAGE_BYTES + 1),
  ) === "too_large",
  ">5 MiB must be rejected client-side",
);
assert(
  fileIssueCopyKey("too_large") === "imageUpload.tooLarge",
  "too-large issue maps to copy key",
);
assert(
  fileIssueCopyKey("unsupported") ===
    "imageUpload.unsupportedType",
  "unsupported issue maps to copy key",
);

const png = makeFile("problem.png", "image/png", 32);
const revoked: string[] = [];
const created: string[] = [];
const firstUrl = assignPreviewUrl(null, png, {
  create(file) {
    const url = `blob:${created.length}:${file.name}`;
    created.push(url);
    return url;
  },
  revoke(url) {
    revoked.push(url);
  },
});
assert(firstUrl === "blob:0:problem.png", "preview URL created");
const jpeg = makeFile("next.jpg", "image/jpeg", 32);
const secondUrl = assignPreviewUrl(firstUrl, jpeg, {
  create(file) {
    const url = `blob:${created.length}:${file.name}`;
    created.push(url);
    return url;
  },
  revoke(url) {
    revoked.push(url);
  },
});
assert(revoked[0] === firstUrl, "old preview URL revoked on replace");
assert(
  secondUrl === "blob:1:next.jpg",
  "replacement preview URL created",
);
revokePreviewUrl(secondUrl, (url) => {
  revoked.push(url);
});
assert(
  revoked[1] === secondUrl,
  "preview URL revoked on cleanup",
);

const extraction = sampleExtraction();
assert(
  canConfirmExtraction(extraction, "2x + 5 = 17", false) === true,
  "valid extraction enables confirmation",
);
assert(
  canConfirmExtraction(extraction, "2x + 5 = 17", true) === false,
  "analyzing disables confirmation",
);
assert(
  canConfirmExtraction(null, "2x + 5 = 17", false) === false,
  "missing extraction disables confirmation",
);
assert(
  canConfirmExtraction(extraction, "   ", false) === false,
  "blank transcription disables confirmation",
);

const unreadable = sampleExtraction({
  transcription: "",
  warnings: ["unreadable"],
  confidence: "low",
});
assert(
  isBlockingUnreadable(unreadable) === true,
  "unreadable is blocking",
);
assert(
  canConfirmExtraction(unreadable, "", false) === false,
  "unreadable disables confirmation",
);

const noProblem = sampleExtraction({
  transcription: "",
  warnings: ["no_problem_found"],
});
assert(
  canConfirmExtraction(noProblem, "typed later", false) ===
    false,
  "no_problem_found disables confirmation",
);

const multiple = sampleExtraction({
  multiple_problems_detected: true,
  warnings: ["multiple_problems_detected"],
});
assert(
  canConfirmExtraction(multiple, "2x + 5 = 17", false) ===
    false,
  "multiple problems disable confirmation",
);

assert(
  warningCopyKey("unreadable") === "imageUpload.unreadable",
  "known warning maps to copy",
);
assert(
  warningCopyKey("cropped") === "imageUpload.cropped",
  "cropped warning maps to copy",
);
assert(
  warningCopyKey("mystery_code") ===
    "imageUpload.genericWarning",
  "unknown warning falls back safely",
);

const ambiguous = sampleExtraction({
  transcription: "a / ? = 4",
  ambiguities: [
    {
      observation: "denominator may be 3 or 5",
      span: null,
      candidates: ["3", "5"],
    },
  ],
  confidence: "low",
});
assert(
  canConfirmExtraction(ambiguous, "a / 3 = 4", false) === true,
  "ambiguity still allows confirmation after edit",
);
assert(
  ambiguous.ambiguities[0].observation.includes("3 or 5"),
  "ambiguity observation preserved",
);
assert(
  confidenceCopyKey("low") === "imageUpload.confidenceLow",
  "low confidence copy key",
);
assert(
  confidenceCopyKey(null) === null,
  "missing confidence has no copy key",
);

const diagram = sampleExtraction({
  diagram_present: true,
  diagram_type: "triangle",
  diagram_facts: [
    {
      kind: "side",
      label: "AB",
      value: "5",
      unit: null,
    },
  ],
});
assert(
  formatDiagramFact(diagram.diagram_facts[0]) === "AB = 5",
  "diagram facts format as label = value",
);

const confirmed = buildConfirmedImageProblem(
  extraction,
  "  2x + 5 = 17  ",
);
assert(
  confirmed.transcription === "2x + 5 = 17",
  "confirmed transcription is trimmed",
);
assert(
  confirmed.language === "en",
  "confirmed language copied",
);
assert(
  confirmed.latexExpressions[0] === "2x + 5 = 17",
  "confirmed formulas copied",
);
assert(
  confirmed.topicHint === "arithmetic",
  "confirmed topic hint copied",
);
assert(
  !("final_answer" in confirmed),
  "confirmed object has no final answer",
);
assert(
  !("previewUrl" in confirmed),
  "confirmed object has no preview URL",
);

assert(
  shouldApplyExtraction(2, 2, png, png) === true,
  "matching request id applies extraction",
);
assert(
  shouldApplyExtraction(3, 2, png, png) === false,
  "stale request cannot overwrite newer image",
);
assert(
  shouldApplyExtraction(2, 2, jpeg, png) === false,
  "response for previous file is ignored",
);

assert(
  mapImageUploadError(new MatPalApiError("bad", 400)) ===
    "imageUpload.invalidImage",
  "400 maps to invalid image",
);
assert(
  mapImageUploadError(
    new MatPalApiError("Upload exceeds the 5 MiB limit.", 400),
  ) === "imageUpload.tooLarge",
  "400 oversized maps to too large",
);
assert(
  mapImageUploadError(
    new MatPalApiError("Unsupported image type.", 400),
  ) === "imageUpload.unsupportedType",
  "400 unsupported maps to type error",
);
assert(
  mapImageUploadError(new MatPalApiError("parse", 422)) ===
    "imageUpload.parseError",
  "422 maps to parse error",
);
assert(
  mapImageUploadError(new MatPalApiError("down", 503)) ===
    "imageUpload.unavailable",
  "503 maps to unavailable",
);
assert(
  mapImageUploadError(new MatPalApiError("slow", 504)) ===
    "imageUpload.timeout",
  "504 maps to timeout",
);
assert(
  mapImageUploadError(new TypeError("Failed to fetch")) ===
    "imageUpload.networkError",
  "network failure maps to network copy",
);
assert(
  mapImageUploadError({ name: "AbortError" }) === null,
  "abort is ignored",
);

assert(
  formatFileSize(512) === "512 B",
  "byte size formatting",
);
assert(
  formatFileSize(2048).endsWith("KB"),
  "kilobyte size formatting",
);

assert(
  isMathOnlyLine("2x + 5 = 17") === true,
  "2x + 5 = 17 is treated as a math formula line",
);

for (const key of IMAGE_UPLOAD_KEYS) {
  assert(
    key in en,
    `EN missing ${key}`,
  );
  assert(
    key in bg,
    `BG missing ${key}`,
  );
  assert(
    translate("en", key) !== key,
    `EN copy missing for ${key}`,
  );
  assert(
    translate("bg", key) !== key,
    `BG copy missing for ${key}`,
  );
}

assert(
  translate("en", "imageUpload.title") ===
    "Upload a math problem",
  "English upload title",
);
assert(
  translate("bg", "imageUpload.title") ===
    "Качи задача по математика",
  "Bulgarian upload title",
);
assert(
  translate("en", "imageUpload.looksCorrect") ===
    "Looks correct",
  "English confirm label",
);
assert(
  translate("bg", "imageUpload.looksCorrect") ===
    "Изглежда правилно",
  "Bulgarian confirm label",
);
assert(
  translate("bg", "imageUpload.analyze") ===
    "Разчети задачата",
  "Bulgarian analyze label",
);
assert(
  !translate("en", "imageUpload.previewAlt").includes("/"),
  "preview alt must not expose a path",
);

assert(
  imageExtractionStatusPath() ===
    "/problems/from-image/status",
  "status path matches backend contract",
);

const availableStatus = {
  available: true,
  reason: null,
};
const unavailableStatus = {
  available: false,
  reason: "vision_provider_unavailable",
};
assert(availableStatus.available === true, "status available");
assert(
  unavailableStatus.available === false,
  "status unavailable",
);
assert(
  unavailableStatus.reason === "vision_provider_unavailable",
  "backend reason is not student-facing copy",
);
assert(
  translate("en", "imageUpload.unavailable").includes(
    "unavailable",
  ),
  "unavailable copy is localized",
);
assert(
  !translate("en", "imageUpload.unavailable").includes(
    "vision_provider_unavailable",
  ),
  "student copy does not show raw status reason",
);

const file = makeFile("problem.png", "image/png", 32);
const extractRequest = buildImageExtractRequest(file, "bg");
assert(
  extractRequest.init.body instanceof FormData,
  "extract uses FormData",
);
const body = extractRequest.init.body as FormData;
assert(
  body.get("file") instanceof File,
  "FormData contains file field",
);
assert(
  extractRequest.url.includes("locale_hint=bg"),
  "locale_hint is a query parameter",
);
assert(
  extractRequest.init.method === "POST",
  "extract is POST",
);
assert(
  extractRequest.init.headers === undefined,
  "extract must not set Content-Type so the browser can add the boundary",
);
assert(
  JSON.stringify(extractRequest.init).indexOf(
    "application/json",
  ) === -1,
  "extract must not force JSON Content-Type",
);

const noHint = buildImageExtractRequest(file);
assert(
  !noHint.url.includes("locale_hint"),
  "locale_hint is omitted when not provided",
);

console.log("image_problem tests passed");
