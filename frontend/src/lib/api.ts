const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "agentics_token";

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getAuthToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

/* ---- Auth ---- */

export type AuthResponse = {
  token: string;
  email: string;
  is_admin?: boolean;
};

async function parseAuthResponse(res: Response): Promise<AuthResponse> {
  const data = await res.json();
  const user = data.user || {};
  const email = user.email || data.email || "";
  const is_admin = user.is_admin ?? false;
  return { token: data.token, email, is_admin };
}

/** Current user (from /me). Call with auth token to get is_admin. */
export type MeResponse = { email: string; is_admin?: boolean; id?: string };

export async function getMe(): Promise<MeResponse | null> {
  const res = await fetch(`${API_URL}/api/auth/me`, { headers: authHeaders() });
  if (!res.ok) return null;
  const data = await res.json();
  return {
    email: data.email ?? "",
    is_admin: data.is_admin ?? false,
    id: data.id,
  };
}

export async function loginApi(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Login failed");
  }
  return parseAuthResponse(res);
}

export async function registerApi(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail || "Registration failed",
    );
  }
  return parseAuthResponse(res);
}

/* ---- Jobs ---- */

export type Job = {
  id: string;
  url: string;
  title: string | null;
  company: string | null;
  created_at?: string;
};

export async function listJobs(limit = 50): Promise<{ jobs: Job[] }> {
  const res = await fetch(`${API_URL}/api/jobs?limit=${limit}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

export type CrawlResponse = {
  status: string;
  message: string;
  query: string;
  max_jobs: number;
  jobs: Job[];
};

export async function runCrawl(
  query: string,
  maxJobs: number,
): Promise<CrawlResponse> {
  const res = await fetch(`${API_URL}/api/jobs/crawl`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, max_jobs: maxJobs }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Crawl failed");
  }
  return res.json();
}

/* ---- Chat ---- */

export type Citation = {
  id: string | null;
  url: string;
  title: string | null;
  company: string | null;
};

export type ChatResponse = {
  reply: string;
  citations: Citation[];
};

export async function postChat(message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message: message.trim() }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Chat failed");
  }
  return res.json();
}
