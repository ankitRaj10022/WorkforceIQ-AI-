import { EmployeeProfile } from "@/components/employee-profile";

type EmployeeProfilePageProps = {
  params: Promise<{
    employeeId: string;
  }>;
};

export default async function EmployeeProfilePage({
  params,
}: EmployeeProfilePageProps) {
  const { employeeId } = await params;

  return (
    <div className="grid gap-6">
      <header className="space-y-3">
        <p className="eyebrow">Employee Detail</p>
        <h1 className="text-4xl font-semibold tracking-[-0.06em]">
          WorkforceIQ employee profile
        </h1>
      </header>
      <EmployeeProfile employeeId={employeeId} />
    </div>
  );
}
