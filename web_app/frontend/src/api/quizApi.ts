import { backendUrl } from "../components/runtime/bindingData";

/**
 * All four screens talk to the backend through this thin API layer.
 * The generated bindingData module already resolves the backend base URL,
 * so every path below is the exact generated route (leading slash kept).
 */
export interface ApiError extends Error {
  status: number;
  detail: string;
}

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const url = backendUrl(path);
  const response = await fetch(url, { ...options, headers: { ...(options.headers ?? {}) } });
  const text = await response.text();
  let payload: any = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const detail =
      (payload && (payload.detail || payload.message)) ||
      `Request failed (${response.status})`;
    const error = new Error(typeof detail === "string" ? detail : JSON.stringify(detail)) as ApiError;
    error.status = response.status;
    error.detail = typeof detail === "string" ? detail : JSON.stringify(detail);
    throw error;
  }
  return payload;
}

export const quizApi = {
  /** Document Upload (R3-R6): POST /pdfdocument/upload/ stores the file,
   * parses and validates it, then creates the PDFDocument row, its Quiz and
   * the extracted Question/Option rows in one transaction. */
  uploadDocument: (file: File): Promise<any> => {
    const body = new FormData();
    body.append("file", file);
    // request() must not set a Content-Type header for FormData:
    // the browser supplies the multipart boundary automatically.
    return request("/pdfdocument/upload/", { method: "POST", body });
  },

  listDocuments: (): Promise<any[]> => request("/pdfdocument/"),

  getDocument: (id: string): Promise<any> => request(`/pdfdocument/${id}/`),

  documentQuestions: (id: string): Promise<any[]> =>
    request(`/pdfdocument/${id}/questions/`),

  deleteDocument: (id: string): Promise<any> => request(`/pdfdocument/${id}/`, { method: "DELETE" }),

  /** Quiz Configuration (R9-R11) */
  startQuiz: (payload: { documentId: string; mode: string; questionOrder: string; questionCount: number }) =>
    request("/attempt/start/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),

  /** Quiz Session (R12-R20) */
  getSession: (attemptId: string, index: number) =>
    request(`/attempt/${attemptId}/session/?index=${index}`),

  submitAnswer: (attemptId: string, questionId: string, selectedOptionId: string) =>
    request(`/attempt/${attemptId}/answer/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionId, selectedOptionId }),
    }),

  /** Results (R21-R24) */
  getResults: (attemptId: string) => request(`/attempt/${attemptId}/results/`),
};

export default quizApi;
