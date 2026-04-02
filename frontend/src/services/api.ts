const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

type RequestOptions = {
  method?: string;
  body?: BodyInit | object;
  token?: string | null;
  headers?: Record<string, string>;
};

function normalizePath(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/")) {
    return `${API_URL}${path}`;
  }
  return `${API_URL}/${path}`;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers || {}) };
  let payload: BodyInit | undefined;

  if (options.body instanceof FormData) {
    payload = options.body;
  } else if (options.body && typeof options.body === "object") {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(options.body);
  } else {
    payload = options.body as BodyInit | undefined;
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(normalizePath(path), {
    method: options.method || "GET",
    headers,
    body: payload,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        detail = data.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function fetchBinary(path: string, token?: string | null): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(normalizePath(path), { headers });
  if (!response.ok) {
    throw new Error(`Audio fetch failed: ${response.status}`);
  }
  return response.blob();
}

export function resolveApiPath(path: string): string {
  return normalizePath(path);
}
