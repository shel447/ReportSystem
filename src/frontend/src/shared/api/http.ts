type RequestOptions = RequestInit & {
  expectText?: boolean;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function requestJson<T>(url: string, options?: RequestOptions): Promise<T> {
  const response = await fetch(url, options);
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
