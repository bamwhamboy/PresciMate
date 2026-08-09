import type {
  AskResponse,
  AuthResponse,
  ExplainResponse,
  ExtractedPrescription,
  HistoryRecord,
  Medicine,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON - fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json();
}

export const api = {
  signup: (name: string, username: string, password: string) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ name, username, password }),
    }),

  login: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getLanguages: () =>
    request<{ languages: string[] }>("/api/languages"),

  extractPrescription: (file: File, token: string) => {
    const form = new FormData();
    form.append("file", file);
    return request<ExtractedPrescription>(
      "/api/prescriptions/extract",
      { method: "POST", body: form },
      token
    );
  },

  explainPrescription: (
    medicines: Medicine[],
    language: string,
    token: string
  ) =>
    request<ExplainResponse>(
      "/api/prescriptions/explain",
      { method: "POST", body: JSON.stringify({ medicines, language }) },
      token
    ),

  askQuestion: (
    question: string,
    medicines: Medicine[],
    language: string,
    token: string
  ) =>
    request<AskResponse>(
      "/api/prescriptions/ask",
      { method: "POST", body: JSON.stringify({ question, medicines, language }) },
      token
    ),

  getHistory: (token: string) =>
    request<HistoryRecord[]>("/api/prescriptions/history", {}, token),

  downloadPdf: async (
    medicines: Medicine[],
    explanation: string,
    language: string,
    token: string
  ) => {
    const res = await fetch(`${API_BASE}/api/prescriptions/pdf`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ medicines, explanation, language }),
    });
    if (!res.ok) throw new ApiError(res.status, "Could not generate PDF");
    return res.blob();
  },
};
