import { NextResponse } from "next/server";
import { EnrichedCompany } from "@/lib/types";
import resultsData from "@/lib/results.json";

const results = resultsData as EnrichedCompany[];

export async function GET() {
  const rows: string[] = [
    ["Contact Name", "Title", "Email", "Email Confidence", "LinkedIn", "Phone", "Company", "Domain", "Industry", "L&D Confirmed", "Confidence", "Source"].join(","),
  ];

  results.forEach((r) => {
    r.contacts.forEach((c) => {
      rows.push([
        `"${c.full_name || ""}"`,
        `"${c.title || ""}"`,
        c.email || "",
        c.email_confidence != null ? `${Math.round(c.email_confidence * 100)}%` : "",
        c.linkedin_url || "",
        c.phone || "",
        `"${r.company.name}"`,
        r.company.domain || "",
        r.company.industry || "",
        r.company.has_lnd_budget ? "Yes" : "No",
        `${Math.round(r.company.confidence_score * 100)}%`,
        c.source || "",
      ].join(","));
    });
  });

  return new NextResponse(rows.join("\n"), {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": "attachment; filename=lnd_contacts.csv",
    },
  });
}
