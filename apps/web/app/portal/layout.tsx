import { redirect } from "next/navigation";

import { PortalShell } from "@/components/portal-shell";
import { readPortalSession } from "@/lib/session";

export default async function PortalLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await readPortalSession();
  if (!session) {
    redirect("/");
  }

  return <PortalShell session={session}>{children}</PortalShell>;
}
