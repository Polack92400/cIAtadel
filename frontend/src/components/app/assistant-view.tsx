"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, MessageSquareText, Plus, Send, ShieldCheck, Trash2, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AnswerText, Sources } from "@/components/app/answer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label, Select, Textarea } from "@/components/ui/input";
import { Alert, Badge, EmptyState, Skeleton, Spinner } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { Conversation, ConversationDetail, Matter, Message, Paginated } from "@/lib/types";
import { cn } from "@/lib/utils";

export function AssistantView({ conversationId }: { conversationId?: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api<Paginated<Conversation>>("/conversations?limit=50"),
  });
  const matters = useQuery({ queryKey: ["matters"], queryFn: () => api<Matter[]>("/matters") });
  const [newMatter, setNewMatter] = useState("");

  const create = useMutation({
    mutationFn: () => api<Conversation>("/conversations", { method: "POST", body: { matter: newMatter || null } }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      router.push(`/assistant/${c.id}`);
    },
  });

  return (
    <div className="grid h-[calc(100vh-9rem)] min-h-[32rem] gap-4 lg:grid-cols-[18rem_1fr]">
      <Card className="flex min-h-0 flex-col">
        <div className="space-y-2 border-b border-border p-3">
          <Label htmlFor="scope" className="text-xs text-muted-foreground">Scope of a new conversation</Label>
          <Select id="scope" value={newMatter} onChange={(e) => setNewMatter(e.target.value)}>
            <option value="">All documents I can access</option>
            {matters.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
          <Button className="w-full" onClick={() => create.mutate()} disabled={create.isPending}>
            {create.isPending ? <Spinner /> : <Plus />} New conversation
          </Button>
          {create.error && <Alert>{create.error.message}</Alert>}
        </div>
        <nav className="min-h-0 flex-1 overflow-y-auto p-2" aria-label="Conversation history">
          {list.isPending && <Skeleton className="h-10" />}
          {list.data?.results.length === 0 && <p className="p-3 text-sm text-muted-foreground">No conversations yet.</p>}
          {list.data?.results.map((c) => (
            <Link key={c.id} href={`/assistant/${c.id}`}
              className={cn("block rounded-md px-3 py-2 text-sm hover:bg-muted", c.id === conversationId && "bg-muted font-medium")}>
              <span className="line-clamp-1">{c.title}</span>
              <span className="text-xs text-muted-foreground">{c.matter_name ?? "All documents"} · {relativeTime(c.updated_at)}</span>
            </Link>
          ))}
        </nav>
      </Card>
      {conversationId ? (
        <ChatPanel key={conversationId} id={conversationId} />
      ) : (
        <Card className="flex items-center justify-center">
          <EmptyState icon={<MessageSquareText />} title="Ask questions about your documents"
            description="Answers are grounded in your firm's indexed PDFs and cite the exact page. Choose a scope, then start a conversation."
            action={<Button onClick={() => create.mutate()} disabled={create.isPending}><Plus /> New conversation</Button>} />
        </Card>
      )}
    </div>
  );
}

function ChatPanel({ id }: { id: string }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<number | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const conv = useQuery({
    queryKey: ["conversations", id],
    queryFn: () => api<ConversationDetail>(`/conversations/${id}`),
    retry: false,
  });

  const ask = useMutation({
    mutationFn: (content: string) => api<Message>(`/conversations/${id}/messages`, { method: "POST", body: { content } }),
    onMutate: (content) => setPending(content),
    onSettled: () => {
      setPending(null);
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
  const remove = useMutation({
    mutationFn: () => api(`/conversations/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      router.push("/assistant");
    },
  });

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [conv.data?.messages.length, pending]);

  if (conv.error) return <Alert>This conversation does not exist or is not yours.</Alert>;
  if (conv.isPending || !conv.data) return <Skeleton className="h-full" />;

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const q = draft.trim();
    if (!q || ask.isPending) return;
    setDraft("");
    ask.mutate(q);
  }
  function cite(n: number, messageId: string) {
    setHighlight(n);
    document.getElementById(`${messageId}`)?.querySelector(`#src-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <Card className="flex min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold">{conv.data.title}</h1>
          <p className="text-xs text-muted-foreground">Scope: {conv.data.matter_name ?? "all documents you can access"}</p>
        </div>
        <Button variant="ghost" size="icon" aria-label="Delete conversation" onClick={() => remove.mutate()}><Trash2 /></Button>
      </div>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4" aria-live="polite">
        {conv.data.messages.length === 0 && !pending && (
          <div className="mx-auto max-w-md pt-10 text-center text-sm text-muted-foreground">
            <ShieldCheck className="mx-auto mb-2 size-6" aria-hidden />
            Ask a question. The assistant only uses passages from documents you are authorised to see, and says so when they do not contain the answer.
          </div>
        )}
        {conv.data.messages.map((m) => (
          <div key={m.id} id={m.id} className="flex gap-3" data-testid={`message-${m.role}`}>
            <div className={cn("flex size-7 shrink-0 items-center justify-center rounded-full",
              m.role === "user" ? "bg-muted" : "bg-primary text-primary-foreground")}>
              {m.role === "user" ? <User className="size-4" /> : <Bot className="size-4" />}
            </div>
            <div className="min-w-0 flex-1">
              {m.role === "user" ? (
                <p className="whitespace-pre-wrap pt-1 text-sm font-medium">{m.content}</p>
              ) : (
                <>
                  {m.insufficient_context && <Badge tone="warning" className="mb-2">Not found in your documents</Badge>}
                  <AnswerText text={m.content} citations={m.citations} onCite={(n) => cite(n, m.id)} />
                  <Sources citations={m.citations} highlight={highlight} insufficient={m.insufficient_context} />
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    {m.model_name} · {m.latency_ms ? `${(m.latency_ms / 1000).toFixed(1)} s` : ""} · AI-generated, verify against the sources. Not legal or accounting advice.
                  </p>
                </>
              )}
            </div>
          </div>
        ))}
        {pending && (
          <>
            <div className="flex gap-3">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted"><User className="size-4" /></div>
              <p className="pt-1 text-sm font-medium">{pending}</p>
            </div>
            <div className="flex items-center gap-2 pl-10 text-sm text-muted-foreground" data-testid="thinking">
              <Spinner /> Searching your documents and drafting an answer… (a local model on CPU can take up to a minute)
            </div>
          </>
        )}
        {ask.error && <Alert>{ask.error.message}</Alert>}
        <div ref={bottom} />
      </div>
      <form onSubmit={submit} className="flex gap-2 border-t border-border p-3">
        <Textarea aria-label="Your question" className="min-h-11 flex-1 resize-none" rows={2} maxLength={4000}
          placeholder="e.g. What notice is required to terminate the agreement?" value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }} />
        <Button type="submit" className="self-end" disabled={!draft.trim() || ask.isPending} aria-label="Send">
          {ask.isPending ? <Spinner /> : <Send />}
        </Button>
      </form>
    </Card>
  );
}
