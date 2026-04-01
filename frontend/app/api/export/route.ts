import { NextResponse } from "next/server";
import { EnrichedCompany } from "@/lib/types";
import resultsData from "@/lib/results.json";

const results = resultsData as EnrichedCompany[];

export async function GET() {
  const rows: string[] = [
    ["Company", "Domain", "Industry", "Confidence", "L&D Confirmed", "L&D Evidence", "Sources", "Contact Name", "Contact Title", "Contact Email", "Contact LinkedIn"].join(","),
  ];

  results.forEach((r) => {
    const base = [
      `"${r.company.name}"`,
      r.company.domain || "",
      r.company.industry || "",
      `${Math.round(r.company.confidence_score * 100)}%`,
      r.company.has_lnd_budget ? "Yes" : "No",
      `"${(r.company.lnd_evidence[0] || "").replace(/"/g, '""').slice(0, 120)}"`,
      `"${r.company.sources.join(", ")}"`,
    ];
    if (r.contacts.length) {
      r.contacts.forEach((c) => {
        rows.push([...base, `"${c.full_name || ""}"`, `"${c.title || ""}"`, c.email || "", c.linkedin_url || ""].join(","));
      });
    } else {
      rows.push([...base, "", "", "", ""].join(","));
    }
  });

  return new NextResponse(rows.join("\n"), {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": "attachment; filename=lnd_companies.csv",
    },
  });
}
