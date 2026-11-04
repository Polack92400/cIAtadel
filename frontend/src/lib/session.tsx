"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { api, setActiveTenant } from "./api";
import type { MembershipSummary, Me } from "./types";

interface SessionValue {
  me: Me;
  membership: MembershipSummary;
  switchTenant: (tenantId: string) => void;
  logout: () => Promise<void>;
}

const SessionContext = React.createContext<SessionValue | null>(null);
const STORAGE_KEY = "ciatadel.activeTenant";

function storedTenant(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const router = useRouter();
  const meQuery = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/auth/me", { noTenant: true }) });
  const [tenantId, setTenantId] = React.useState<string | null>(null);

  const me = meQuery.data;
  const membership = React.useMemo(() => {
    if (!me || me.memberships.length === 0) return null;
    const wanted = tenantId ?? storedTenant();
    return me.memberships.find((m) => m.tenant_id === wanted) ?? me.memberships[0];
  }, [me, tenantId]);

  // Set synchronously during render so the very first queries carry the header.
  if (membership) setActiveTenant(membership.tenant_id);

  const switchTenant = React.useCallback(
    (id: string) => {
      try {
        window.localStorage.setItem(STORAGE_KEY, id);
      } catch {
        /* storage unavailable: in-memory only */
      }
      setActiveTenant(id);
      setTenantId(id);
      // Drop every cached tenant-scoped response.
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
      router.push("/dashboard");
    },
    [qc, router],
  );

  const logout = React.useCallback(async () => {
    await api("/auth/logout", { method: "POST", noTenant: true }).catch(() => undefined);
    setActiveTenant(null);
    qc.clear();
    window.location.href = "/login";
  }, [qc]);

  if (meQuery.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading your workspace…
      </div>
    );
  }
  if (meQuery.isError || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Session expired. Redirecting to sign-in…
      </div>
    );
  }
  if (!membership) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-sm">
        <p className="font-medium">You are not a member of any firm yet.</p>
        <p className="text-muted-foreground">Ask a firm administrator to add you.</p>
        <button className="text-primary underline" onClick={logout}>
          Sign out
        </button>
      </div>
    );
  }
  return (
    <SessionContext.Provider value={{ me, membership, switchTenant, logout }}>
      {/* key: remount the workspace when the firm changes */}
      <React.Fragment key={membership.tenant_id}>{children}</React.Fragment>
    </SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}
