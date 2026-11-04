"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, FolderKanban, MessageSquareText, Upload } from "lucide-react";
import Link from "next/link";
import { StatusBadge } from "@/components/app/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, EmptyState, PageHeader, Skeleton } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<Dashboard>("/dashboard"),
    refetchInterval: (q) => {
      const s = q.state.data?.documents_by_status;
      return s && s.pending + s.processing > 0 ? 3000 : false;
    },
  });

  if (error) return <Alert>{error.message}</Alert>;
  if (isPending || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      </div>
    );
  }
  const s = data.documents_by_status;
  const stats = [
    { label: "Documents", value: data.document_total, icon: FileText, href: "/documents" },
    { label: "Ready to query", value: s.ready, icon: FileText, href: "/documents?status=ready" },
    { label: "Matters", value: data.matter_count, icon: FolderKanban, href: "/matters" },
    { label: "My conversations", value: data.conversation_count, icon: MessageSquareText, href: "/assistant" },
  ];

  return (
    <>
      <PageHeader title={data.tenant.name} description="Overview of your firm's workspace"
        actions={
          <>
            <Link href="/documents?upload=1" className={buttonVariants({ variant: "outline" })}><Upload /> Upload PDF</Link>
            <Link href="/assistant" className={buttonVariants()}><MessageSquareText /> Ask the assistant</Link>
          </>
        } />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((st) => (
          <Link key={st.label} href={st.href}>
            <Card className="transition-colors hover:border-primary/40">
              <CardContent className="flex items-center justify-between p-5">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{st.label}</p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">{st.value}</p>
                </div>
                <st.icon className="size-5 text-muted-foreground" aria-hidden />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      {(s.pending > 0 || s.processing > 0 || s.failed > 0) && (
        <div className="mt-4 flex flex-wrap gap-2 text-sm text-muted-foreground">
          Processing status:
          {s.pending > 0 && <span>{s.pending} queued</span>}
          {s.processing > 0 && <span>· {s.processing} indexing</span>}
          {s.failed > 0 && <span className="text-destructive">· {s.failed} failed</span>}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Recent documents</CardTitle></CardHeader>
          <CardContent>
            {data.recent_documents.length === 0 ? (
              <EmptyState icon={<FileText />} title="No documents yet" description="Upload a PDF to get started." />
            ) : (
              <ul className="divide-y divide-border">
                {data.recent_documents.map((d) => (
                  <li key={d.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <Link href={`/documents/${d.id}`} className="block truncate text-sm font-medium hover:underline">{d.title}</Link>
                      <p className="text-xs text-muted-foreground">{d.matter_name ?? "General"} · {relativeTime(d.created_at)}</p>
                    </div>
                    <StatusBadge status={d.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent conversations</CardTitle></CardHeader>
          <CardContent>
            {data.recent_conversations.length === 0 ? (
              <EmptyState icon={<MessageSquareText />} title="No conversations yet"
                description="Ask a question about your documents." />
            ) : (
              <ul className="divide-y divide-border">
                {data.recent_conversations.map((c) => (
                  <li key={c.id} className="py-2.5">
                    <Link href={`/assistant/${c.id}`} className="block truncate text-sm font-medium hover:underline">{c.title}</Link>
                    <p className="text-xs text-muted-foreground">{c.matter_name ?? "All accessible documents"} · {relativeTime(c.updated_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
