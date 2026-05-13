import { EmployeeDirectory } from "@/components/employee-directory";

export default function EmployeesPage() {
  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Employees</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          Search and inspect the workforce directory
        </h1>
      </header>
      <EmployeeDirectory />
    </div>
  );
}
