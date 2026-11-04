"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Search, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { StatusBadge } from "@/components/app/status-badge";
import { UploadDialog } from "@/components/app/upload-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, EmptyState, PageHeader, Skeleton } from "@/components/ui/misc";
import { Table, TBody, Td, Th, THead } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatBytes, formatDate, roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { DocumentItem, Matter, Paginated } from "@/lib/types";

function DocumentsView() {
  const { membership } = useSession();
  const params = useSearchParams();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [status, setStatus] = useState(params.get("status") ?? "");
  const [matter, setMatter] = useState(params.get("matter") ?? "");
  const [uploadOpen, setUploadOpen] = useState(params.get("upload") === "1");
  const canWrite = roleAtLeast(membership.role, "member");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);

  const matters = useQuery({ queryKey: ["matters"], queryFn: () => api<Matter[]>("/matters") });
  const qs = new URLSearchParams({ limit: "100" });
  if (debounced) qs.set("search", debounced);
  if (status) qs.set("status", status);
  if (matter) qs.set("matter", matter);
  const docs = useQuery({
    queryKey: ["documents", debounced, status, matter],
    queryFn: () => api<Paginated<DocumentItem>>(`/documents?${qs}`),
    refetchInterval: (q) =>
      q.state.data?.results.some((d) => d.status === "pending" || d.status === "processing") ? 2500 : false,
  });

  return (
    <>
      <PageHeader title="Documents" description="PDFs stored privately for your firm and indexed for the assistant."
        actions={canWrite && <Button onClick={() => setUploadOpen(true)}><Upload /> Upload PDF</Button>} />

      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" aria-hidden />
          <Input aria-label="Search documents" placeholder="Search by title or file name" className="pl-8"
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select aria-label="Filter by status" className="w-40" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="ready">Ready</option>
          <option value="processing">Indexing</option>
          <option value="pending">Queued</option>
          <option value="failed">Failed</option>
        </Select>
        <Select aria-label="Filter by matter" className="w-64" value={matter} onChange={(e) => setMatter(e.target.value)}>
          <option value="">All matters</option>
          <option value="none">General (no matter)</option>
          {matters.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </Select>
      </div>

      {docs.error && <Alert>{docs.error.message}</Alert>}
      <Card>
        {docs.isPending ? (
          <div className="space-y-2 p-4">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-10" />)}</div>
        ) : docs.data && docs.data.results.length === 0 ? (
          <EmptyState icon={<FileText />} title="No documents found"
            description={debounced || status || matter ? "Try other filters." : "Upload your first PDF."} />
        ) : (
          <Table>
            <THead>
              <tr><Th>Title</Th><Th>Matter</Th><Th>Status</Th><Th className="text-right">Size</Th><Th>Uploaded</Th></tr>
            </THead>
            <TBody>
              {docs.data?.results.map((d) => (
                <tr key={d.id} className="cursor-pointer hover:bg-muted/40" onClick={() => router.push(`/documents/${d.id}`)}>
                  <Td>
                    <Link href={`/documents/${d.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>{d.title}</Link>
                    <p className="text-xs text-muted-foreground">{d.original_filename}</p>
                  </Td>
                  <Td className="text-muted-foreground">{d.matter_name ?? "General"}</Td>
                  <Td><StatusBadge status={d.status} /></Td>
                  <Td className="text-right tabular-nums text-muted-foreground">{formatBytes(d.size_bytes)}</Td>
                  <Td className="text-muted-foreground">{formatDate(d.created_at)}</Td>
                </tr>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} matters={matters.data ?? []} />
    </>
  );
}

export default function DocumentsPage() {
  return <Suspense><DocumentsView /></Suspense>;
}
