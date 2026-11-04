import { Badge, Spinner } from "@/components/ui/misc";
import type { DocumentStatus } from "@/lib/types";

const MAP: Record<DocumentStatus, { label: string; tone: "neutral" | "success" | "warning" | "danger" | "info" }> = {
  pending: { label: "Queued", tone: "neutral" },
  processing: { label: "Indexing", tone: "info" },
  ready: { label: "Ready", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const s = MAP[status];
  return (
    <Badge tone={s.tone} data-testid="doc-status">
      {(status === "pending" || status === "processing") && <Spinner className="size-3" />}
      {s.label}
    </Badge>
  );
}
