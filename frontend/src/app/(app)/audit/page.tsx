"use client";

import { useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, Badge, EmptyState, PageHeader, Skeleton } from "@/components/ui/misc";
import { Table, TBody, Td, Th, THead } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { AuditEvent, Paginated } from "@/lib/types";

const TONE = { security: "danger", document: "info", conversation: "neutral", admin: "warning" } as const;

export default function AuditPage() {
  const { membership } = useSession();
  const [category, setCategory] = useState("");
  const [actor, setActor] = useState("");
  const qs = new URLSearchParams({ limit: "100" });
  if (category) qs.set("category", category);
  if (actor.trim()) qs.set("actor", actor.trim());
  const events = useQuery({
    queryKey: ["audit", category, actor],
    queryFn: () => api<Paginated<AuditEvent>>(`/audit-events?${qs}`),
    enabled: roleAtLeast(membership.role, "admin"),
  });

  if (!roleAtLeast(membership.role, "admin")) return <Alert>The audit log is restricted to administrators.</Alert>;

  return (
    <>
      <PageHeader title="Audit log" description="Append-only record of security events, user activity and document access in this firm." />
      <div className="mb-4 flex flex-wrap gap-2">
        <Select aria-label="Category" className="w-48" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          <option value="security">Security</option>
          <option value="document">Documents</option>
          <option value="conversation">Assistant</option>
          <option value="admin">Administration</option>
        </Select>
        <Input aria-label="Filter by user" placeholder="Filter by user email" className="w-64" value={actor} onChange={(e) => setActor(e.target.value)} />
      </div>
      {events.error && <Alert>{events.error.message}</Alert>}
      <Card>
        {events.isPending ? <div className="p-4"><Skeleton className="h-40" /></div> :
          events.data?.results.length === 0 ? <EmptyState icon={<ScrollText />} title="No events" /> : (
            <Table>
              <THead><tr><Th>When</Th><Th>User</Th><Th>Event</Th><Th>Target</Th><Th>IP</Th></tr></THead>
              <TBody>
                {events.data?.results.map((e) => (
                  <tr key={e.id}>
                    <Td className="whitespace-nowrap text-muted-foreground">{formatDate(e.created_at)}</Td>
                    <Td>{e.actor_email || "—"}</Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <Badge tone={TONE[e.category]}>{e.category}</Badge>
                        <code className="text-xs">{e.action}</code>
                        {e.outcome !== "success" && <Badge tone="danger">{e.outcome}</Badge>}
                      </div>
                    </Td>
                    <Td className="max-w-64 truncate text-muted-foreground" title={e.target_label}>{e.target_label || e.target_type || "—"}</Td>
                    <Td className="text-xs text-muted-foreground">{e.ip_address ?? "—"}</Td>
                  </tr>
                ))}
              </TBody>
            </Table>
          )}
      </Card>
    </>
  );
}
