import { AuditLogView } from "@/components/audit-log-view";

export default function AuditPage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Audit Trail</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Governed event history
        </h1>
      </header>
      <AuditLogView />
    </div>
  );
}
