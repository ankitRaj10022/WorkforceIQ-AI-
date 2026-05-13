import { ComplianceConsole } from "@/components/compliance-console";

export default function CompliancePage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Compliance</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Privacy and data request console
        </h1>
      </header>
      <ComplianceConsole />
    </div>
  );
}
