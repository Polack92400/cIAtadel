"use client";

import * as React from "react";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Renders model output as plain React elements (no HTML injection): supports
 * **bold** and [S<n>] citation markers, which become buttons that highlight the
 * matching source.
 */
export function AnswerText({
  text,
  citations,
  onCite,
}: {
  text: string;
  citations: Citation[];
  onCite: (n: number) => void;
}) {
  const known = new Set(citations.map((c) => c.number));
  const paragraphs = text.split(/\n{2,}/);
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {paragraphs.map((p, i) => (
        <p key={i} className="whitespace-pre-wrap">
          {renderInline(p, known, onCite)}
        </p>
      ))}
    </div>
  );
}

function renderInline(text: string, known: Set<number>, onCite: (n: number) => void) {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\[S\d{1,2}\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push(<strong key={k++} className="font-semibold">{tok.slice(2, -2)}</strong>);
    } else {
      const n = Number(tok.slice(2, -1));
      out.push(
        known.has(n) ? (
          <button key={k++} type="button" onClick={() => onCite(n)}
            className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-primary/10 px-1 align-baseline text-[11px] font-semibold text-primary hover:bg-primary/20"
            aria-label={`Source ${n}`}>
            {n}
          </button>
        ) : (
          tok
        ),
      );
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Sources({
  citations,
  highlight,
  insufficient,
}: {
  citations: Citation[];
  highlight: number | null;
  insufficient: boolean;
}) {
  const [showAll, setShowAll] = React.useState(false);
  const used = citations.filter((c) => c.used);
  const other = citations.filter((c) => !c.used);
  if (citations.length === 0) return null;
  // If the model answered without explicit [n] markers, be transparent and
  // show every passage it was given rather than hiding the provenance.
  const uncited = used.length === 0 && !insufficient;
  const highlightedHidden = highlight !== null && other.some((c) => c.number === highlight);
  const shown = showAll || highlightedHidden || uncited ? [...used, ...other] : used;
  const heading =
    used.length > 0
      ? "Cited sources from your documents"
      : uncited
        ? "Passages provided to the assistant (no explicit citation in the answer)"
        : "Passages searched";
  return (
    <div className="mt-3 space-y-2" data-testid="sources">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{heading}</p>
      <ul className="space-y-2">
        {shown.map((c) => (
          <li key={c.number} id={`src-${c.number}`}
            className={cn(
              "rounded-md border border-border bg-card p-3 text-xs transition-colors",
              !c.used && "opacity-70",
              highlight === c.number && "border-primary ring-2 ring-primary/30",
            )}>
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded bg-primary/10 px-1 font-semibold text-primary">{c.number}</span>
              {c.document ? (
                <a href={`/documents/${c.document}`} className="font-medium hover:underline">{c.document_title}</a>
              ) : (
                <span className="font-medium">{c.document_title} (deleted)</span>
              )}
              {c.page_number && <span className="text-muted-foreground">page {c.page_number}</span>}
              {!c.used && !uncited && <span className="text-muted-foreground">· retrieved, not cited</span>}
            </div>
            {c.excerpt && <Excerpt text={c.excerpt} />}
          </li>
        ))}
      </ul>
      {other.length > 0 && !highlightedHidden && !uncited && (
        <button type="button" onClick={() => setShowAll((v) => !v)}
          className="text-xs font-medium text-primary hover:underline">
          {showAll ? "Hide" : "Show"} {other.length} other retrieved passage{other.length > 1 ? "s" : ""}
        </button>
      )}
    </div>
  );
}

function Excerpt({ text }: { text: string }) {
  const [open, setOpen] = React.useState(false);
  const long = text.length > 320;
  return (
    <>
      <p className={cn("whitespace-pre-wrap text-muted-foreground", !open && long && "line-clamp-4")}>{text}</p>
      {long && (
        <button type="button" onClick={() => setOpen((v) => !v)} className="mt-1 text-primary hover:underline">
          {open ? "Show less" : "Show full passage"}
        </button>
      )}
    </>
  );
}
