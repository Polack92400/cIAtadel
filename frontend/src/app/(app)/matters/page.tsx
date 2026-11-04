"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderKanban, Lock, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Alert, Badge, EmptyState, PageHeader, Skeleton, Spinner } from "@/components/ui/misc";
import { Table, TBody, Td, Th, THead } from "@/components/ui/table";
import { api } from "@/lib/api";
import { roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Matter, Member } from "@/lib/types";

export default function MattersPage() {
  const { membership } = useSession();
  const qc = useQueryClient();
  const isAdmin = roleAtLeast(membership.role, "admin");
  const canCreate = roleAtLeast(membership.role, "member");
  const matters = useQuery({ queryKey: ["matters"], queryFn: () => api<Matter[]>("/matters") });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api<Member[]>("/members"), enabled: isAdmin });
  const [editing, setEditing] = useState<Matter | "new" | null>(null);

  return (
    <>
      <PageHeader title="Matters" description="Organise documents by client matter or engagement. Restricted matters act as ethical walls."
        actions={canCreate && <Button onClick={() => setEditing("new")}><Plus /> New matter</Button>} />
      {matters.error && <Alert>{matters.error.message}</Alert>}
      <Card>
        {matters.isPending ? (
          <div className="p-4"><Skeleton className="h-24" /></div>
        ) : matters.data?.length === 0 ? (
          <EmptyState icon={<FolderKanban />} title="No matters yet" />
        ) : (
          <Table>
            <THead><tr><Th>Matter</Th><Th>Reference</Th><Th>Access</Th><Th className="text-right">Documents</Th><Th /></tr></THead>
            <TBody>
              {matters.data?.map((m) => (
                <tr key={m.id}>
                  <Td>
                    <Link href={`/documents?matter=${m.id}`} className="font-medium hover:underline">{m.name}</Link>
                    {m.description && <p className="line-clamp-1 text-xs text-muted-foreground">{m.description}</p>}
                  </Td>
                  <Td className="text-muted-foreground">{m.reference || "—"}</Td>
                  <Td>
                    {m.is_restricted ? (
                      <Badge tone="warning"><Lock className="size-3" /> Restricted ({m.allowed_members.length})</Badge>
                    ) : (
                      <Badge>All members</Badge>
                    )}
                  </Td>
                  <Td className="text-right tabular-nums">{m.document_count}</Td>
                  <Td className="text-right">
                    {canCreate && <Button size="sm" variant="ghost" onClick={() => setEditing(m)}>Edit</Button>}
                  </Td>
                </tr>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
      {editing && (
        <MatterDialog matter={editing === "new" ? null : editing} isAdmin={isAdmin} members={members.data ?? []}
          onClose={() => setEditing(null)}
          onSaved={() => { qc.invalidateQueries({ queryKey: ["matters"] }); setEditing(null); }} />
      )}
    </>
  );
}

function MatterDialog({ matter, isAdmin, members, onClose, onSaved }: {
  matter: Matter | null; isAdmin: boolean; members: Member[]; onClose: () => void; onSaved: () => void;
}) {
  const [name, setName] = useState(matter?.name ?? "");
  const [reference, setReference] = useState(matter?.reference ?? "");
  const [description, setDescription] = useState(matter?.description ?? "");
  const [restricted, setRestricted] = useState(matter?.is_restricted ?? false);
  const [allowed, setAllowed] = useState<string[]>(matter?.allowed_members ?? []);
  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = { name, reference, description };
      if (isAdmin) Object.assign(body, { is_restricted: restricted, allowed_members: allowed });
      return matter
        ? api(`/matters/${matter.id}`, { method: "PATCH", body })
        : api("/matters", { method: "POST", body });
    },
    onSuccess: onSaved,
  });
  return (
    <Dialog open onClose={onClose} title={matter ? "Edit matter" : "New matter"}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        {save.error && <Alert>{save.error.message}</Alert>}
        <div className="space-y-1.5"><Label htmlFor="m-name">Name</Label>
          <Input id="m-name" required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="m-ref">Reference</Label>
          <Input id="m-ref" maxLength={64} value={reference} onChange={(e) => setReference(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="m-desc">Description</Label>
          <Textarea id="m-desc" maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} /></div>
        {isAdmin && (
          <fieldset className="space-y-2 rounded-md border border-border p-3">
            <label className="flex items-center gap-2 text-sm font-medium">
              <input type="checkbox" checked={restricted} onChange={(e) => setRestricted(e.target.checked)} />
              Restrict access (ethical wall)
            </label>
            {restricted && (
              <div className="max-h-40 space-y-1 overflow-y-auto pl-6">
                <p className="text-xs text-muted-foreground">Admins and owners always have access. Also allow:</p>
                {members.filter((m) => m.role === "member" || m.role === "viewer").map((m) => (
                  <label key={m.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={allowed.includes(m.id)}
                      onChange={(e) => setAllowed(e.target.checked ? [...allowed, m.id] : allowed.filter((x) => x !== m.id))} />
                    {m.full_name || m.email} <span className="text-muted-foreground">({m.email})</span>
                  </label>
                ))}
              </div>
            )}
          </fieldset>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending && <Spinner />} Save</Button>
        </div>
      </form>
    </Dialog>
  );
}
