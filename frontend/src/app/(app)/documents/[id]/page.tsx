"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { StatusBadge } from "@/components/app/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/input";
import { Alert, PageHeader, Skeleton, Spinner } from "@/components/ui/misc";
import { api, downloadDocument } from "@/lib/api";
import { formatBytes, formatDate, roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { DocumentItem, Matter } from "@/lib/types";

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { me, membership } = useSession();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const doc = useQuery({
    queryKey: ["documents", "detail", id],
    queryFn: () => api<DocumentItem>(`/documents/${id}`),
    refetchInterval: (q) => (q.state.data && ["pending", "processing"].includes(q.state.data.status) ? 2000 : false),
    retry: false,
  });
  const matters = useQuery({ queryKey: ["matters"], queryFn: () => api<Matter[]>("/matters") });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["documents"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };
  const move = useMutation({
    mutationFn: (matter: string | null) => api(`/documents/${id}`, { method: "PATCH", body: { matter } }),
    onSuccess: invalidate,
    onError: (e) => setActionError(e.message),
  });
  const del = useMutation({
    mutationFn: () => api(`/documents/${id}`, { method: "DELETE" }),
    onSuccess: () => { invalidate(); router.push("/documents"); },
    onError: (e) => { setConfirmDelete(false); setActionError(e.message); },
  });
  const reprocess = useMutation({
    mutationFn: () => api(`/documents/${id}/reprocess`, { method: "POST" }),
    onSuccess: invalidate,
    onError: (e) => setActionError(e.message),
  });

  if (doc.error) {
    return (
      <div className="space-y-4">
        <Link href="/documents" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline"><ArrowLeft className="size-4" /> Documents</Link>
        <Alert>This document does not exist or you do not have access to it.</Alert>
      </div>
    );
  }
  if (doc.isPending || !doc.data) return <Skeleton className="h-64" />;
  const d = doc.data;
  const isAdmin = roleAtLeast(membership.role, "admin");
  const canEdit = roleAtLeast(membership.role, "member");
  const canDelete = isAdmin || (canEdit && d.uploaded_by_email === me.email);

  return (
    <>
      <Link href="/documents" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="size-4" /> Documents
      </Link>
      <PageHeader title={d.title} description={d.original_filename}
        actions={
          <>
            <Button variant="outline" onClick={() => downloadDocument(d.id, d.original_filename).catch((e) => setActionError(e.message))}>
              <Download /> Download
            </Button>
            {isAdmin && d.status === "failed" && (
              <Button variant="outline" onClick={() => reprocess.mutate()} disabled={reprocess.isPending}><RefreshCw /> Retry</Button>
            )}
            {canDelete && <Button variant="destructive" onClick={() => setConfirmDelete(true)}><Trash2 /> Delete</Button>}
          </>
        } />
      {actionError && <Alert className="mb-4">{actionError}</Alert>}
      {d.status === "failed" && (
        <Alert className="mb-4">Processing failed: {d.error_message || d.error_code}</Alert>
      )}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
              <div><dt className="text-muted-foreground">Status</dt><dd className="mt-1"><StatusBadge status={d.status} /></dd></div>
              <div><dt className="text-muted-foreground">Size</dt><dd className="mt-1">{formatBytes(d.size_bytes)}</dd></div>
              <div><dt className="text-muted-foreground">Pages</dt><dd className="mt-1">{d.page_count ?? "—"}</dd></div>
              <div><dt className="text-muted-foreground">Indexed passages</dt><dd className="mt-1">{d.chunk_count}</dd></div>
              <div><dt className="text-muted-foreground">Uploaded by</dt><dd className="mt-1">{d.uploaded_by_email ?? "—"}</dd></div>
              <div><dt className="text-muted-foreground">Uploaded</dt><dd className="mt-1">{formatDate(d.created_at)}</dd></div>
              <div><dt className="text-muted-foreground">Indexed</dt><dd className="mt-1">{formatDate(d.processed_at)}</dd></div>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Matter</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <Select aria-label="Matter" disabled={!canEdit || move.isPending} value={d.matter ?? ""}
              onChange={(e) => move.mutate(e.target.value || null)}>
              <option value="">General (no matter)</option>
              {matters.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </Select>
            <p className="text-xs text-muted-foreground">The assistant only uses documents from matters you can access.</p>
          </CardContent>
        </Card>
      </div>
      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete this document?"
        description="The file, its indexed passages and its search entries are removed. Past answers keep only the title.">
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button variant="destructive" onClick={() => del.mutate()} disabled={del.isPending}>
            {del.isPending && <Spinner />} Delete permanently
          </Button>
        </div>
      </Dialog>
    </>
  );
}
