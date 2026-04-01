import { NextResponse } from "next/server";
import resultsData from "@/lib/results.json";

export async function GET() {
  return NextResponse.json(resultsData);
}
