import { DashboardOverview } from "@/components/dashboard-overview";

export default function PortalPage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Overview</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Workforce operating picture
        </h1>
        <p className="max-w-3xl text-sm leading-7 text-muted sm:text-base">
          This portal is bound to the current WorkforceIQ backend: same
          identities, same RBAC, same reports, same audit surfaces.
        </p>
      </header>
      <DashboardOverview />
    </div>
  );
}
