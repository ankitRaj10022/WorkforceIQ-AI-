import { NextResponse } from "next/server";

import { readFrontendSessionPayload } from "@/lib/session";

export async function GET() {
  return NextResponse.json(await readFrontendSessionPayload());
}
