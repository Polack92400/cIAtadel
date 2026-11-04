"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, UserPlus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label, Select } from "@/components/ui/input";
import { Alert, Badge, PageHeader, Skeleton, Spinner } from "@/components/ui/misc";
import { Table, TBody, Td, Th, THead } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, ROLE_LABEL, roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Role, Tenant } from "@/lib/types";

const ROLES: Role[] = ["viewer", "member", "admin", "owner"];

export default function AdminPage() {
  const { membership, me } = useSession();
  const qc = useQueryClient();
  const tenant = useQuery({ queryKey: ["tenant"], queryFn: () => api<Tenant>("/tenant") });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api<Member[]>("/members") });
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rename = useMutation({
    mutationFn: (n: string) => api<Tenant>("/tenant", { method: "PATCH", body: { name: n } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tenant"] }); qc.invalidateQueries({ queryKey: ["me"] }); setName(null); },
    onError: (e) => setError(e.message),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Member> }) => api(`/members/${id}`, { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members"] }),
    onError: (e) => setError(e.message),
  });

  if (!roleAtLeast(membership.role, "admin")) {
    return <Alert>Firm administration is restricted to administrators.</Alert>;
  }
  const grantable = ROLES.filter((r) => roleAtLeast(membership.role, r));

  return (
    <>
      <PageHeader title="Firm administration" description="Members, roles and firm information." />
      {error && <Alert className="mb-4">{error}</Alert>}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Building2 className="size-4" /> Firm</CardTitle>
            <CardDescription>Workspace identity</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {tenant.isPending || !tenant.data ? <Skeleton className="h-20" /> : (
              <>
                <form className="space-y-1.5" onSubmit={(e) => { e.preventDefault(); if (name) rename.mutate(name); }}>
                  <Label htmlFor="firm-name">Name</Label>
                  <div className="flex gap-2">
                    <Input id="firm-name" value={name ?? tenant.data.name} onChange={(e) => setName(e.target.value)} />
                    {name !== null && name !== tenant.data.name && <Button type="submit" disabled={rename.isPending}>Save</Button>}
                  </div>
                </form>
                <p><span className="text-muted-foreground">Identifier:</span> {tenant.data.slug}</p>
                <p><span className="text-muted-foreground">Active members:</span> {tenant.data.member_count}</p>
                <p><span className="text-muted-foreground">Created:</span> {formatDate(tenant.data.created_at)}</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div><CardTitle>Members</CardTitle><CardDescription>Only members of this firm can see its data.</CardDescription></div>
            <Button size="sm" onClick={() => setAdding(true)}><UserPlus /> Add member</Button>
          </CardHeader>
          {members.isPending ? <div className="p-4"><Skeleton className="h-32" /></div> : (
            <Table>
              <THead><tr><Th>Member</Th><Th>Role</Th><Th>Status</Th><Th>Last sign-in</Th></tr></THead>
              <TBody>
                {members.data?.map((m) => {
                  const self = m.email === me.email;
                  const locked = self || !roleAtLeast(membership.role, m.role);
                  return (
                    <tr key={m.id}>
                      <Td><p className="font-medium">{m.full_name || m.email}</p><p className="text-xs text-muted-foreground">{m.email}</p></Td>
                      <Td>
                        <Select aria-label={`Role of ${m.email}`} className="h-8 w-36" disabled={locked} value={m.role}
                          onChange={(e) => { setError(null); update.mutate({ id: m.id, body: { role: e.target.value as Role } }); }}>
                          {(locked ? ROLES : grantable).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                        </Select>
                      </Td>
                      <Td>
                        <button disabled={locked} className="disabled:cursor-not-allowed"
                          onClick={() => { setError(null); update.mutate({ id: m.id, body: { is_active: !m.is_active } }); }}
                          title={locked ? undefined : m.is_active ? "Deactivate" : "Reactivate"}>
                          {m.is_active ? <Badge tone="success">Active</Badge> : <Badge>Deactivated</Badge>}
                        </button>
                      </Td>
                      <Td className="text-muted-foreground">{formatDate(m.last_login)}</Td>
                    </tr>
                  );
                })}
              </TBody>
            </Table>
          )}
        </Card>
      </div>
      <AddMemberDialog open={adding} grantable={grantable} onClose={() => setAdding(false)}
        onAdded={() => { qc.invalidateQueries({ queryKey: ["members"] }); setAdding(false); }} />
    </>
  );
}

function AddMemberDialog({ open, grantable, onClose, onAdded }: {
  open: boolean; grantable: Role[]; onClose: () => void; onAdded: () => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [password, setPassword] = useState("");
  const add = useMutation({
    mutationFn: () => api("/members", { method: "POST", body: { email, full_name: fullName, role, initial_password: password || undefined } }),
    onSuccess: () => { setEmail(""); setFullName(""); setPassword(""); onAdded(); },
  });
  return (
    <Dialog open={open} onClose={onClose} title="Add a member"
      description="Controlled user creation: new accounts get the initial password you set; existing accounts are simply added to this firm.">
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        {add.error && <Alert>{add.error.message}</Alert>}
        <div className="space-y-1.5"><Label htmlFor="nm-email">Email</Label>
          <Input id="nm-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="nm-name">Full name</Label>
          <Input id="nm-name" value={fullName} onChange={(e) => setFullName(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="nm-role">Role</Label>
          <Select id="nm-role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {grantable.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </Select></div>
        <div className="space-y-1.5"><Label htmlFor="nm-pwd">Initial password (new accounts, min. 12 characters)</Label>
          <Input id="nm-pwd" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={add.isPending}>{add.isPending && <Spinner />} Add member</Button>
        </div>
      </form>
    </Dialog>
  );
}
