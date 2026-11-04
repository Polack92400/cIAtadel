/**
 * Thin client for the Django API.
 *
 * - Same-origin requests only (`/api/v1/...`, proxied by Next.js).
 * - Credentials are HttpOnly cookies: tokens are never readable from JS.
 * - The active tenant is sent as a *hint* header; Django verifies it against
 *   the user's memberships on every request.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
    public requestId?: string,
  ) {
    super(`API error ${status}`);
  }
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.split("=")[1];
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit & { tenantId?: string } = {},
): Promise<T> {
  const { tenantId, headers, ...rest } = init;
  const method = (rest.method ?? "GET").toUpperCase();
  const h = new Headers(headers);
  h.set("Accept", "application/json");
  if (tenantId) h.set("X-Tenant-ID", tenantId);
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = readCookie("csrftoken");
    if (csrf) h.set("X-CSRFToken", csrf);
  }

  const res = await fetch(`/api/v1${path}`, { ...rest, headers: h, credentials: "same-origin" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.error?.detail ?? body, res.headers.get("X-Request-ID") ?? undefined);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
