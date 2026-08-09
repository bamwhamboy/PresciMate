export interface Medicine {
  name: string;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  instructions: string | null;
}

export interface ExtractedPrescription {
  patient_name: string | null;
  medicines: Medicine[];
  notes: string | null;
  low_confidence: boolean;
}

export interface Interaction {
  drug_a: string;
  drug_b: string;
  severity: string;
  description: string;
}

export interface Grounding {
  flagged: boolean;
  ungrounded_claims: string[];
}

export interface ExplainResponse {
  explanation: string;
  interactions: Interaction[];
  grounding: Grounding;
}

export interface AskResponse {
  answer: string;
  grounding: Grounding;
  emergency: boolean;
}

export interface HistoryRecord {
  username: string;
  prescription_id: string;
  medicines: string;
  explanation: string;
  language: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  name: string;
  username: string;
}
