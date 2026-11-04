/**
 * Client for the Django API.
 *
 * - Same-origin only (`/api/v1/...`, proxied server-side by Next.js).
 * - Credentials are HttpOnly cookies: tokens are never readable from JS.
 * - Unsafe methods send Django's CSRF token (double-submit cookie).
 * - The active firm is sent as a *hint* header; Django verifies membership.
 * - A 401 triggers one silent refresh (rotating refresh token), then a retry.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
    public requestId?: string,
  ) {
    super(formatDetail(detail) || `Request failed (${status})`);
  }
}

function formatDetail(detail: unknown): string {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(formatDetail).join(" ");
  if (typeof detail === "object") {
    const obj = detail as Record<string, unknown>;
    if ("detail" in obj) return formatDetail(obj.detail);
    return Object.entries(obj)
      .filter(([k]) => k !== "existing_id" && k !== "status")
      .map(([k, v]) =>
        ["non_field_errors", "file", "detail"].includes(k) ? formatDetail(v) : `${k}: ${formatDetail(v)}`,
      )
      .join(" ");
  }
  return String(detail);
}

let activeTenantId: string | null = null;
export function setActiveTenant(id: string | null) {
  activeTenantId = id;
}

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const hit = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return hit ? decodeURIComponent(hit.split("=")[1]) : undefined;
}

let csrfPromise: Promise<void> | null = null;
async function ensureCsrf(): Promise<void> {
  if (readCookie("csrftoken")) return;
  csrfPromise ??= fetch("/api/v1/auth/csrf", { credentials: "same-origin" }).then(() => {
    csrfPromise = null;
  });
  return csrfPromise;
}

let refreshPromise: Promise<boolean> | null = null;
async function refreshSession(): Promise<boolean> {
  refreshPromise ??= (async () => {
    await ensureCsrf();
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": readCookie("csrftoken") ?? "" },
    });
    refreshPromise = null;
    return res.ok;
  })();
  return refreshPromise;
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; noTenant?: boolean; retry?: boolean };

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const { body, noTenant, retry = true, headers, ...rest } = opts;
  const method = (rest.method ?? "GET").toUpperCase();
  const h = new Headers(headers);
  h.set("Accept", "application/json");
  if (!noTenant && activeTenantId) h.set("X-Tenant-ID", activeTenantId);

  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    h.set("Content-Type", "application/json");
    payload = JSON.stringify(body);
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    await ensureCsrf();
    h.set("X-CSRFToken", readCookie("csrftoken") ?? "");
  }

  const res = await fetch(`/api/v1${path}`, {
    ...rest,
    method,
    headers: h,
    body: payload,
    credentials: "same-origin",
  });

  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, { ...opts, retry: false });
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data?.error?.detail ?? data, res.headers.get("X-Request-ID") ?? undefined);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const downloadUrl = (id: string) => `/api/v1/documents/${id}/download`;

/** Downloads go through fetch so the tenant header is sent; then saved as a blob. */
export async function downloadDocument(id: string, filename: string) {
  const res = await fetch(downloadUrl(id), {
    credentials: "same-origin",
    headers: activeTenantId ? { "X-Tenant-ID": activeTenantId } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
