"use client";

import {
  Building2,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  ScrollText,
  ShieldCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Select } from "@/components/ui/input";
import { Badge } from "@/components/ui/misc";
import { ROLE_LABEL, roleAtLeast } from "@/lib/format";
import { useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, min: "viewer" },
  { href: "/documents", label: "Documents", icon: FileText, min: "viewer" },
  { href: "/matters", label: "Matters", icon: FolderKanban, min: "viewer" },
  { href: "/assistant", label: "AI assistant", icon: MessageSquareText, min: "viewer" },
  { href: "/admin", label: "Firm administration", icon: Users, min: "admin" },
  { href: "/audit", label: "Audit log", icon: ScrollText, min: "admin" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, membership, switchTenant, logout } = useSession();
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
        <div className="flex items-center gap-2 px-5 py-5 text-base font-semibold">
          <ShieldCheck className="size-5" aria-hidden /> cIAtadel
        </div>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
          {NAV.filter((n) => roleAtLeast(membership.role, n.min)).map((n) => {
            const active = pathname === n.href || pathname.startsWith(`${n.href}/`);
            return (
              <Link key={n.href} href={n.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active ? "bg-white/10 font-medium text-white" : "text-sidebar-foreground/75 hover:bg-white/5 hover:text-white",
                )}>
                <n.icon className="size-4" aria-hidden /> {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-4 text-xs text-sidebar-foreground/60">
          Fictional data only · POC
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between gap-4 border-b border-border bg-card/90 px-4 backdrop-blur md:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <Building2 className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            {me.memberships.length > 1 ? (
              <Select aria-label="Active firm" className="h-8 w-auto max-w-72 font-medium"
                value={membership.tenant_id} onChange={(e) => switchTenant(e.target.value)}>
                {me.memberships.map((m) => (
                  <option key={m.tenant_id} value={m.tenant_id}>{m.tenant_name}</option>
                ))}
              </Select>
            ) : (
              <span className="truncate text-sm font-medium" data-testid="active-firm">{membership.tenant_name}</span>
            )}
            <Badge tone="info">{ROLE_LABEL[membership.role]}</Badge>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">{me.email}</span>
            <button onClick={logout}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
              <LogOut className="size-4" aria-hidden /> Sign out
            </button>
          </div>
        </header>
        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-b border-border bg-card px-2 py-1 md:hidden" aria-label="Main mobile">
          {NAV.filter((n) => roleAtLeast(membership.role, n.min)).map((n) => (
            <Link key={n.href} href={n.href}
              className={cn("whitespace-nowrap rounded px-2.5 py-1.5 text-xs",
                pathname.startsWith(n.href) ? "bg-muted font-medium" : "text-muted-foreground")}>
              {n.label}
            </Link>
          ))}
        </nav>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
