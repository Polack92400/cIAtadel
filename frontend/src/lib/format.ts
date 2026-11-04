export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

const dtf = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });
export function formatDate(iso: string | null | undefined): string {
  return iso ? dtf.format(new Date(iso)) : "—";
}

export function relativeTime(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return formatDate(iso);
}

export const ROLE_LABEL: Record<string, string> = {
  owner: "Owner",
  admin: "Administrator",
  member: "Member",
  viewer: "Viewer",
};
const RANK: Record<string, number> = { viewer: 10, member: 20, admin: 30, owner: 40 };
export const roleAtLeast = (role: string | undefined, min: string) => (RANK[role ?? ""] ?? 0) >= RANK[min];
