import { ShieldCheck } from "lucide-react";

// Phase 1 placeholder. Phase 4 replaces this with the login flow and the
// authenticated workspace shell.
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-8 w-8 text-primary" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight">cIAtadel</h1>
      </div>
      <p className="text-muted-foreground">
        Private AI workspace for professional firms. Proof of concept — fictional data only.
      </p>
      <p className="text-sm text-muted-foreground">Scaffolding in place. Sign-in arrives in Phase 4.</p>
    </main>
  );
}
