export type ExtractionLanguage = "en" | "bg" | "unknown";

export type ExtractionConfidence = "low" | "medium" | "high";

export interface ImageExtractionStatus {
  available: boolean;
  reason: string | null;
}

export interface ExtractedDiagramFact {
  kind: string;
  label: string | null;
  value: string | null;
  unit: string | null;
}

export interface ExtractedAmbiguity {
  observation: string;
  span: string | null;
  candidates: string[];
}

export interface SourceImageMetadata {
  content_type: string;
  byte_size: number;
}

export interface ExtractedProblem {
  transcription: string;
  language: ExtractionLanguage;
  problem_type_hint: string | null;
  topic_hint: string | null;
  latex_expressions: string[];
  diagram_present: boolean;
  diagram_type: string | null;
  diagram_facts: ExtractedDiagramFact[];
  ambiguities: ExtractedAmbiguity[];
  warnings: string[];
  multiple_problems_detected: boolean;
  confidence: ExtractionConfidence | null;
  source: SourceImageMetadata;
}

export interface ConfirmedImageProblem {
  transcription: string;
  language: ExtractionLanguage;
  latexExpressions: string[];
  topicHint: string | null;
  problemTypeHint: string | null;
}
