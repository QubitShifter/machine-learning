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
  buildConfirmedProblemRequest,
  buildImageExtractRequest,
  buildImportedProblemRequest,
  canConfirmExtraction,
  canStartGuidedSolve,
  confidenceCopyKey,
  fileIssueCopyKey,
  formatDiagramFact,
  formatFileSize,
  imageExtractionStatusPath,
  catalogSessionStartProblemId,
  importedGuidanceErrorIsRetryable,
  importedHandoffPlan,
  importedProblemPath,
  importedSessionStartRequest,
  mapImportedHandoffError,
  nextPendingImportedProblemId,
  isBlockingUnreadable,
  mapImageUploadError,
  mapImportedProblemError,
  MAX_IMAGE_BYTES,
  readImportedProblemId,
  revokePreviewUrl,
  shouldApplyExtraction,
  shouldApplyImportedStart,
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
  "imageUpload.solveWithGuidance",
  "imageUpload.preparingGuidance",
  "imageUpload.guidanceUnsupported",
  "imageUpload.guidanceUnavailable",
  "imageUpload.guidanceTimeout",
  "imageUpload.guidanceFailed",
  "imageUpload.sessionStartFailed",
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

assert(
  !("imageUpload.confirmedNextStep" in en),
  "old next-phase placeholder key is gone from EN",
);
assert(
  !("imageUpload.confirmedNextStep" in bg),
  "old next-phase placeholder key is gone from BG",
);
assert(
  translate("en", "imageUpload.solveWithGuidance") ===
    "Solve with guidance",
  "English solve with guidance label",
);
assert(
  translate("bg", "imageUpload.solveWithGuidance") ===
    "Реши с насоки",
  "Bulgarian solve with guidance label",
);
assert(
  !translate("en", "imageUpload.solveWithGuidance")
    .toLowerCase()
    .includes("next step"),
  "solve action is not a next-phase placeholder",
);

const confirmedEn = buildConfirmedImageProblem(
  sampleExtraction({
    transcription: "2x + 5 = 17",
    language: "en",
    latex_expressions: ["2x + 5 = 17"],
    topic_hint: "geometry",
    problem_type_hint: "triangle",
  }),
  "2x + 5 = 17",
);
const enRequest = buildConfirmedProblemRequest(
  confirmedEn,
  "bg",
);
assert(enRequest.transcription === "2x + 5 = 17", "EN transcription mapped");
assert(enRequest.language === "en", "known EN language is not overwritten by BG UI");
assert(
  enRequest.latex_expressions[0] === "2x + 5 = 17",
  "latexExpressions map to latex_expressions",
);
assert(enRequest.topic_hint === "geometry", "topicHint maps to topic_hint");
assert(
  enRequest.problem_type_hint === "triangle",
  "problemTypeHint maps to problem_type_hint",
);
assert(
  Object.keys(enRequest).join(",") ===
    "transcription,language,latex_expressions,topic_hint,problem_type_hint",
  "confirmed request has only the backend contract fields",
);

const confirmedBg = buildConfirmedImageProblem(
  sampleExtraction({
    transcription: "Иван има 4 ябълки.",
    language: "bg",
  }),
  "Иван има 4 ябълки.",
);
assert(
  buildConfirmedProblemRequest(confirmedBg, "en").language ===
    "bg",
  "known BG language is not overwritten by EN UI",
);

const confirmedUnknown = buildConfirmedImageProblem(
  sampleExtraction({ language: "unknown" }),
  "2x + 5 = 17",
);
assert(
  buildConfirmedProblemRequest(confirmedUnknown, "bg")
    .language === "bg",
  "unknown language falls back to BG UI locale",
);
assert(
  buildConfirmedProblemRequest(confirmedUnknown, "en")
    .language === "en",
  "unknown language falls back to EN UI locale",
);

const importedHttp = buildImportedProblemRequest(
  confirmedEn,
  "en",
);
assert(importedHttp.init.method === "POST", "imported create is POST");
assert(
  importedHttp.url.endsWith("/problems/from-confirmed"),
  "imported create uses from-confirmed",
);
assert(
  importedProblemPath() === "/problems/from-confirmed",
  "imported path matches backend contract",
);
assert(
  (importedHttp.init.headers as Record<string, string>)[
    "Content-Type"
  ] === "application/json",
  "imported create sends JSON Content-Type",
);
assert(
  typeof importedHttp.init.body === "string",
  "imported create uses a JSON string body, not FormData",
);
const importedBody = JSON.parse(importedHttp.init.body as string);
assert(
  JSON.stringify(importedBody) === JSON.stringify(enRequest),
  "imported JSON body matches confirmed mapping",
);
assert(
  !JSON.stringify(importedBody).toLowerCase().includes("image"),
  "imported request has no image field",
);
assert(
  !JSON.stringify(importedBody).includes("base64"),
  "imported request has no base64",
);
assert(
  !JSON.stringify(importedBody).includes("blob:"),
  "imported request has no object URL",
);
assert(
  !JSON.stringify(importedBody).includes("filename"),
  "imported request has no filename",
);
assert(
  !("source" in importedBody),
  "imported request has no source metadata",
);
assert(
  !("previewUrl" in importedBody),
  "imported request has no preview URL",
);

const createdResponse = {
  problem_id: "imported_generated_abc123",
  topic: "unknown_numbers",
  language: "en",
  title: "Unknown number",
};
assert(
  readImportedProblemId(createdResponse) ===
    "imported_generated_abc123",
  "successful create returns problem_id",
);
const sessionStart = importedSessionStartRequest(
  createdResponse.problem_id,
  "student-1",
  "en",
);
assert(
  sessionStart.problem_id === createdResponse.problem_id,
  "imported problem_id goes through existing session-start path",
);
assert(sessionStart.student_id === "student-1", "session start keeps student id");
assert(sessionStart.language === "en", "session start keeps UI language");
assert(
  !("mastery" in sessionStart) && !("progress" in sessionStart),
  "session start does not send mastery or progress",
);

assert(
  canStartGuidedSolve(confirmedEn, false) === true,
  "confirmed state can start guided solve",
);
assert(
  canStartGuidedSolve(confirmedEn, true) === false,
  "duplicate Solve click is prevented while starting",
);
assert(
  canStartGuidedSolve(
    confirmedEn,
    false,
    "imageUpload.guidanceUnsupported",
  ) === false,
  "unsupported error still allows Edit again instead of Solve",
);
assert(
  importedGuidanceErrorIsRetryable(
    "imageUpload.guidanceUnavailable",
  ) === true,
  "503 offers Try again",
);
assert(
  importedGuidanceErrorIsRetryable(
    "imageUpload.guidanceTimeout",
  ) === true,
  "504 offers Try again",
);
assert(
  importedGuidanceErrorIsRetryable("imageUpload.networkError") ===
    true,
  "network failure offers Try again",
);
assert(
  importedGuidanceErrorIsRetryable(
    "imageUpload.guidanceUnsupported",
  ) === false,
  "unsupported 422 is not a retry prompt",
);
assert(
  importedGuidanceErrorIsRetryable(
    "imageUpload.guidanceFailed",
  ) === false,
  "planning failure is not auto-retried",
);

assert(
  mapImportedProblemError(
    new MatPalApiError("unsupported_problem_type", 422),
  ) === "imageUpload.guidanceUnsupported",
  "422 unsupported mapped correctly",
);
assert(
  mapImportedProblemError(
    new MatPalApiError("Imported solution plan could not be parsed.", 422),
  ) === "imageUpload.guidanceFailed",
  "422 planning failure mapped correctly",
);
assert(
  mapImportedProblemError(
    new MatPalApiError("Imported problem planner unavailable.", 503),
  ) === "imageUpload.guidanceUnavailable",
  "503 unavailable mapped correctly",
);
assert(
  mapImportedProblemError(
    new MatPalApiError("Imported problem planner timed out.", 504),
  ) === "imageUpload.guidanceTimeout",
  "504 timeout mapped correctly",
);
assert(
  mapImportedProblemError(new TypeError("Failed to fetch")) ===
    "imageUpload.networkError",
  "network failure mapped correctly",
);
assert(
  mapImportedProblemError({ name: "AbortError" }) === null,
  "imported abort is ignored",
);

const retryRequest = buildConfirmedProblemRequest(
  confirmedEn,
  "en",
);
assert(
  retryRequest.transcription === confirmedEn.transcription,
  "retry preserves confirmed transcription",
);

assert(
  shouldApplyImportedStart(4, 4, confirmedEn, confirmedEn) ===
    true,
  "matching imported start applies",
);
assert(
  shouldApplyImportedStart(5, 4, confirmedEn, confirmedEn) ===
    false,
  "stale imported start cannot launch tutor after reset",
);
assert(
  shouldApplyImportedStart(4, 4, null, confirmedEn) === false,
  "imported start after unconfirm/reset is ignored",
);
assert(
  shouldApplyImportedStart(4, 4, confirmedBg, confirmedEn) ===
    false,
  "imported start for a replaced confirmation is ignored",
);

assert(
  !JSON.stringify(buildConfirmedProblemRequest(confirmedEn, "en"))
    .includes("mastery"),
  "no mastery field in imported request",
);

const createdId = "imported_generated_abc123";
const firstHandoff = importedHandoffPlan(null);
assert(
  firstHandoff.callFromConfirmed === true,
  "imported creation is called when no pending problem_id exists",
);
assert(
  firstHandoff.startProblemId === null,
  "session start waits for created problem_id",
);

let pendingId = nextPendingImportedProblemId({
  pendingProblemId: null,
  createdProblemId: createdId,
});
assert(
  pendingId === createdId,
  "successful create retains pending imported problem_id",
);

const startFailure = mapImportedHandoffError(
  new Error("MAT-PAL API request failed with 500"),
  "start",
);
assert(
  startFailure === "imageUpload.sessionStartFailed",
  "session-start-specific error is shown, not a planning failure",
);
assert(
  importedGuidanceErrorIsRetryable(startFailure) === true,
  "session-start failure offers Try again",
);
assert(
  translate("en", "imageUpload.sessionStartFailed").includes(
    "tutoring session",
  ),
  "EN session-start copy exists",
);
assert(
  translate("bg", "imageUpload.sessionStartFailed").includes(
    "учебната сесия",
  ),
  "BG session-start copy exists",
);

const retryHandoff = importedHandoffPlan(pendingId);
assert(
  retryHandoff.callFromConfirmed === false,
  "retry does NOT call /problems/from-confirmed again",
);
assert(
  retryHandoff.startProblemId === createdId,
  "retry uses existing imported problem_id",
);

pendingId = nextPendingImportedProblemId({
  pendingProblemId: pendingId,
  clear: true,
});
assert(
  pendingId === null,
  "Edit again clears pending problem_id",
);
assert(
  importedHandoffPlan(pendingId).callFromConfirmed === true,
  "after Edit again, create is required again",
);

pendingId = nextPendingImportedProblemId({
  pendingProblemId: createdId,
  clear: true,
});
assert(
  pendingId === null,
  "Analyze another clears pending problem_id",
);

pendingId = nextPendingImportedProblemId({
  pendingProblemId: createdId,
  createdProblemId: createdId,
});
pendingId = nextPendingImportedProblemId({
  pendingProblemId: pendingId,
  clear: true,
});
assert(
  pendingId === null,
  "changing confirmed content cannot reuse stale problem_id",
);
assert(
  importedHandoffPlan(null).callFromConfirmed === true,
  "new confirmed text must create a new imported problem",
);

assert(
  mapImportedHandoffError(
    new MatPalApiError("unsupported_problem_type", 422),
    "create",
  ) === "imageUpload.guidanceUnsupported",
  "planning 422 unsupported mapping is unchanged",
);
assert(
  mapImportedHandoffError(
    new MatPalApiError("Imported solution plan could not be parsed.", 422),
    "create",
  ) === "imageUpload.guidanceFailed",
  "planning 422 failure mapping is unchanged",
);
assert(
  mapImportedHandoffError(
    new MatPalApiError("Imported problem planner unavailable.", 503),
    "create",
  ) === "imageUpload.guidanceUnavailable",
  "planning 503 mapping is unchanged",
);
assert(
  mapImportedHandoffError(
    new MatPalApiError("Imported problem planner timed out.", 504),
    "create",
  ) === "imageUpload.guidanceTimeout",
  "planning 504 mapping is unchanged",
);
assert(
  mapImportedHandoffError(
    new TypeError("Failed to fetch"),
    "create",
  ) === "imageUpload.networkError",
  "planning network mapping is unchanged",
);

assert(
  catalogSessionStartProblemId(
    "grade4_reverse_reasoning_001",
    true,
  ) === "grade4_reverse_reasoning_001",
  "catalog session start still uses the selected catalog problem",
);
assert(
  catalogSessionStartProblemId(
    "grade4_reverse_reasoning_001",
    false,
  ) === null,
  "catalog session start still requires a visible catalog problem",
);
assert(
  catalogSessionStartProblemId("", true) === null,
  "catalog session start does not fall back to an imported problem_id",
);

console.log("image_problem tests passed");
