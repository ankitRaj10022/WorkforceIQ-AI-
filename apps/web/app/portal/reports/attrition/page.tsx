import { AttritionReport } from "@/components/attrition-report";

export default function AttritionReportPage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Reports</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Attrition exposure report
        </h1>
      </header>
      <AttritionReport />
    </div>
  );
}
