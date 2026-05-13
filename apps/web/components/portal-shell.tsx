import Link from "next/link";

import type { PortalSessionState } from "@/lib/session";

type PortalShellProps = {
  session: PortalSessionState;
  children: React.ReactNode;
};

const navItems = [
  { href: "/portal", label: "Overview" },
  { href: "/portal/employees", label: "Employees" },
  { href: "/portal/department-health", label: "Department Health" },
  { href: "/portal/reports/attrition", label: "Attrition Report" },
  { href: "/portal/audit", label: "Audit Trail" },
  { href: "/portal/compliance", label: "Compliance" },
];

export function PortalShell({ session, children }: PortalShellProps) {
  return (
    <div className="shell-grid min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-7xl gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="panel-strong flex flex-col justify-between rounded-[2rem] p-5 sm:p-6">
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="eyebrow">WorkforceIQ Portal</p>
              <div>
                <h1 className="text-2xl font-semibold tracking-[-0.05em]">
                  Cloud Operations Console
                </h1>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Cognito-authenticated workspace on top of the WorkforceIQ API.
                </p>
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-border bg-white/70 p-4">
              <p className="eyebrow">Signed In</p>
              <p className="mt-3 text-base font-semibold">{session.user.email}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="badge badge-neutral">{session.user.role}</span>
                {session.user.employee_id ? (
                  <span className="badge badge-success mono">
                    {session.user.employee_id}
                  </span>
                ) : null}
              </div>
            </div>

            <nav className="space-y-2">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-2xl border border-transparent px-4 py-3 text-sm font-medium text-foreground transition hover:border-border hover:bg-white/72"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="space-y-3">
            <div className="rounded-[1.5rem] border border-border bg-surface-ink px-4 py-4 text-white">
              <p className="eyebrow !text-white/60">Session</p>
              <p className="mt-3 text-sm leading-6 text-white/80">
                Login tracked in WorkforceIQ with refresh rotation and logout
                revocation.
              </p>
            </div>
            <Link href="/auth/logout" className="button-secondary w-full">
              Sign Out
            </Link>
          </div>
        </aside>

        <div className="panel-strong rounded-[2rem] p-4 sm:p-6 lg:p-7">
          {children}
        </div>
      </div>
    </div>
  );
}
