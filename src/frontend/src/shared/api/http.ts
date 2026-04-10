type RequestOptions = RequestInit & {
  expectText?: boolean;
};

export const CHATBI_API_PREFIX = "/rest/chatbi/v1";
export const DEV_API_PREFIX = "/rest/dev";

export function chatbiPath(path: string): string {
  return `${CHATBI_API_PREFIX}${normalizePath(path)}`;
}

export function devPath(path: string): string {
  return `${DEV_API_PREFIX}${normalizePath(path)}`;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function requestJson<T>(url: string, options?: RequestOptions): Promise<T> {
  const response = await fetch(url, withApiHeaders(url, options));
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  if (options?.expectText) {
    return (await response.text()) as T;
  }
  return response.json() as Promise<T>;
}

export function postJson<TResponse>(url: string, body: unknown): Promise<TResponse> {
  return requestJson<TResponse>(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

function withApiHeaders(url: string, options?: RequestOptions): RequestOptions | undefined {
  if (!isChatbiUrl(url)) {
    return options;
  }

  const nextHeaders = new Headers(options?.headers ?? {});
  if (!nextHeaders.has("X-User-Id")) {
    nextHeaders.set("X-User-Id", "default");
  }

  return {
    ...options,
    headers: nextHeaders,
  };
}

function isChatbiUrl(url: string): boolean {
  return (
    url.startsWith(CHATBI_API_PREFIX)
    || url.includes(`${CHATBI_API_PREFIX}/`)
    || url.includes(CHATBI_API_PREFIX)
  );
}

export function putJson<TResponse>(url: string, body: unknown): Promise<TResponse> {
  return requestJson<TResponse>(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

export async function deleteJson(url: string): Promise<void> {
  await requestJson(url, { method: "DELETE" });
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      return payload.detail;
    }
    if (typeof payload?.message === "string") {
      return payload.message;
    }
  } catch {
    // Ignore invalid json.
  }
  return `请求失败 (${response.status})`;
}

function normalizePath(path: string): string {
  if (!path) {
    return "";
  }
  return path.startsWith("/") ? path : `/${path}`;
}
