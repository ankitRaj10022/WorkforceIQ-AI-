import { DepartmentHealthPanel } from "@/components/department-health-panel";

export default function DepartmentHealthPage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Department Health</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Department operating condition
        </h1>
      </header>
      <DepartmentHealthPanel />
    </div>
  );
}
