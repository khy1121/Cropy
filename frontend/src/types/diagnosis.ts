export interface PredictionItem {
  name: string;
  confidence: number;
}

export interface PesticideInfo {
  name: string;
  dilution?: string;
  usage?: string;
  active_ingredient?: string;
  safety_notes?: string;
  safety: {
    phi_days?: number;
    reentry_hours?: number;
  };
}

export type Severity = "low" | "medium" | "high";

export interface RecaptureCandidate {
  name: string;
  cue: string;
}

export interface RecaptureGuidance {
  region: string;
  instruction: string;
  margin: number;
  candidates: RecaptureCandidate[];
}

export interface DiagnoseResponse {
  id: string;
  disease_name: string;
  crop_type?: string;
  category?: "disease" | "normal";
  severity?: Severity;
  confidence: number;
  top_predictions: PredictionItem[];
  description?: string;
  causes: string[];
  pesticides: PesticideInfo[];
  prevention: string[];
  image_url?: string;
  refined_image_url?: string | null;
  created_at: string;
  recapture?: RecaptureGuidance | null;
}

export interface DiagnosisSummary {
  id: string;
  disease_name: string;
  confidence: number;
  crop_type?: string;
  image_url?: string;
  created_at: string;
}

export interface PaginatedHistory {
  items: DiagnosisSummary[];
  total: number;
  page: number;
  size: number;
}
