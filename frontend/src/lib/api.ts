import type {
  AnalysisResponse,
  AnalyzeRequest,
  BootstrapResponse,
  WriteBackResponse,
} from "../types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function loadBootstrap(): Promise<BootstrapResponse> {
  return request<BootstrapResponse>("/api/bootstrap");
}

export function analyzeChange(payload: AnalyzeRequest): Promise<AnalysisResponse> {
  return request<AnalysisResponse>("/api/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function writeBack(
  analysis: AnalysisResponse,
): Promise<WriteBackResponse> {
  return requestJson<WriteBackResponse>("/api/write-back", {
    run_id: analysis.run_id,
    approved: true,
  });
}

function requestJson<T>(url: string, payload: unknown): Promise<T> {
  return request<T>(url, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
