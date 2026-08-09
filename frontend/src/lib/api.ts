import type {
  AnalysisResponse,
  AnalyzeRequest,
  BootstrapResponse,
  WriteBackResponse,
} from "../types";

const LOCAL_SESSION_HASH_KEY = "contextloop_token";
const LOCAL_SESSION_STORAGE_KEY = "contextloop.local-session";
const MIN_LOCAL_SESSION_TOKEN_LENGTH = 32;

function localSessionToken(): string | null {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  const suppliedToken = fragment.get(LOCAL_SESSION_HASH_KEY);
  if (suppliedToken !== null) {
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    if (suppliedToken.length >= MIN_LOCAL_SESSION_TOKEN_LENGTH) {
      window.sessionStorage.setItem(LOCAL_SESSION_STORAGE_KEY, suppliedToken);
      return suppliedToken;
    }
    window.sessionStorage.removeItem(LOCAL_SESSION_STORAGE_KEY);
    return null;
  }

  const storedToken = window.sessionStorage.getItem(LOCAL_SESSION_STORAGE_KEY);
  return storedToken && storedToken.length >= MIN_LOCAL_SESSION_TOKEN_LENGTH
    ? storedToken
    : null;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const sessionToken = localSessionToken();
  if (sessionToken) headers.set("X-ContextLoop-Token", sessionToken);

  const response = await fetch(url, {
    ...init,
    headers,
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
