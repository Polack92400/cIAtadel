"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label, Select } from "@/components/ui/input";
import { Alert, Spinner } from "@/components/ui/misc";
import { api } from "@/lib/api";
import type { DocumentItem, Matter } from "@/lib/types";

const MAX_MB = 25;

export function UploadDialog({ open, onClose, matters }: { open: boolean; onClose: () => void; matters: Matter[] }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [matter, setMatter] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("file", file as File);
      if (title) fd.append("title", title);
      if (matter) fd.append("matter", matter);
      return api<DocumentItem>("/documents", { method: "POST", body: fd });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      reset();
      onClose();
    },
  });

  function reset() {
    setFile(null);
    setTitle("");
    setMatter("");
    setClientError(null);
    mutation.reset();
  }

  function pick(f: File | null) {
    setClientError(null);
    if (f && !f.name.toLowerCase().endsWith(".pdf")) setClientError("Only PDF files are accepted.");
    else if (f && f.size > MAX_MB * 1024 * 1024) setClientError(`File too large (max ${MAX_MB} MB).`);
    setFile(f);
  }

  return (
    <Dialog open={open} onClose={() => { reset(); onClose(); }} title="Upload a PDF"
      description="The document is stored privately for your firm, then indexed for the assistant.">
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        {(clientError || mutation.error) && <Alert>{clientError ?? mutation.error?.message}</Alert>}
        <div className="space-y-1.5">
          <Label htmlFor="file">PDF file (max {MAX_MB} MB)</Label>
          <Input id="file" type="file" accept="application/pdf,.pdf" required
            onChange={(e) => pick(e.target.files?.[0] ?? null)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="title">Title (optional)</Label>
          <Input id="title" value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)}
            placeholder="Defaults to the file name" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="matter">Matter</Label>
          <Select id="matter" value={matter} onChange={(e) => setMatter(e.target.value)}>
            <option value="">General (no matter)</option>
            {matters.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => { reset(); onClose(); }}>Cancel</Button>
          <Button type="submit" disabled={!file || !!clientError || mutation.isPending}>
            {mutation.isPending ? <Spinner /> : <Upload />} Upload
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
