"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { EnrichedCompany } from "@/lib/types";
import resultsData from "@/lib/results.json";

const results = resultsData as EnrichedCompany[];

function getAllSources(data: EnrichedCompany[]): string[] {
  const s = new Set<string>();
  data.forEach((r) => r.company.sources.forEach((src) => s.add(src)));
  return Array.from(s).sort();
}

export default function Home() {
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [sortBy, setSortBy] = useState("confidence");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [confirmedOnly, setConfirmedOnly] = useState(false);
  const [hasEmailOnly, setHasEmailOnly] = useState(false);

  const allSources = useMemo(() => getAllSources(results), []);

  const filtered = useMemo(() => {
    let data = [...results];
    const q = search.toLowerCase();
    if (q) {
      data = data.filter(
        (r) =>
          r.company.name.toLowerCase().includes(q) ||
          (r.company.domain && r.company.domain.toLowerCase().includes(q)) ||
          (r.company.industry && r.company.industry.toLowerCase().includes(q))
      );
    }
    if (source) data = data.filter((r) => r.company.sources.includes(source));
    if (confirmedOnly) data = data.filter((r) => r.company.has_lnd_budget);
    if (hasEmailOnly) data = data.filter((r) => r.contacts.some((c) => c.email));

    const sortFns: Record<string, (a: EnrichedCompany, b: EnrichedCompany) => number> = {
      confidence: (a, b) => a.company.confidence_score - b.company.confidence_score,
      name: (a, b) => a.company.name.localeCompare(b.company.name),
      contacts: (a, b) => a.contacts.length - b.contacts.length,
    };
    const fn = sortFns[sortBy] || sortFns.confidence;
    data.sort((a, b) => (sortDir === "desc" ? -fn(a, b) : fn(a, b)));
    return data;
  }, [search, source, sortBy, sortDir, confirmedOnly, hasEmailOnly]);

  const stats = useMemo(() => ({
    total: filtered.length,
    confirmed: filtered.filter((r) => r.company.has_lnd_budget).length,
    withContacts: filtered.filter((r) => r.contacts.length > 0).length,
    withEmail: filtered.filter((r) => r.contacts.some((c) => c.email)).length,
    totalContacts: filtered.reduce((sum, r) => sum + r.contacts.length, 0),
  }), [filtered]);

  const exportCsv = () => {
    const rows = [
      ["Company", "Domain", "Industry", "Confidence", "L&D Confirmed", "L&D Evidence", "Sources", "Contact Name", "Contact Title", "Contact Email", "Contact LinkedIn"].join(","),
    ];
    filtered.forEach((r) => {
      const base = [
        `"${r.company.name}"`, r.company.domain || "", r.company.industry || "",
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
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lnd_companies.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const confColor = (score: number) =>
    score >= 0.7 ? "bg-emerald-500" : score >= 0.4 ? "bg-amber-500" : "bg-red-400";
  const confBorder = (score: number) =>
    score >= 0.7 ? "border-l-emerald-500" : score >= 0.4 ? "border-l-amber-500" : "border-l-gray-600";

  return (
    <>
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { n: stats.total, label: "Companies Found", color: "text-white" },
          { n: stats.confirmed, label: "Confirmed L&D", color: "text-emerald-400" },
          { n: stats.withContacts, label: "With HR Contacts", color: "text-blue-400" },
          { n: stats.withEmail, label: "With Email", color: "text-violet-400" },
          { n: stats.totalContacts, label: "Total Contacts", color: "text-white" },
        ].map((s) => (
          <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:-translate-y-0.5 transition-transform">
            <div className={`text-3xl font-bold ${s.color}`}>{s.n}</div>
            <div className="text-xs text-gray-500 mt-1 font-medium">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm w-60 focus:outline-none focus:border-violet-500 placeholder-gray-600"
          />
          <select value={source} onChange={(e) => setSource(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500">
            <option value="">All Sources</option>
            {allSources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500">
            <option value="confidence">Confidence</option>
            <option value="name">Name</option>
            <option value="contacts">Contacts</option>
          </select>
          <select value={sortDir} onChange={(e) => setSortDir(e.target.value as "desc" | "asc")}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm w-20 focus:outline-none focus:border-violet-500">
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
            <input type="checkbox" checked={confirmedOnly} onChange={(e) => setConfirmedOnly(e.target.checked)}
              className="accent-violet-500 w-3.5 h-3.5" />
            Confirmed L&D
          </label>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
            <input type="checkbox" checked={hasEmailOnly} onChange={(e) => setHasEmailOnly(e.target.checked)}
              className="accent-violet-500 w-3.5 h-3.5" />
            Has Email
          </label>
          <button onClick={exportCsv}
            className="ml-auto bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-900/50 border-b border-gray-800">
                  {["Company", "Domain", "Industry", "L&D Evidence", "Confidence", "Sources", "Contacts"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.company.normalized_name} className={`border-l-3 ${confBorder(r.company.confidence_score)} border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors`}>
                    <td className="px-4 py-3">
                      <Link href={`/company/${encodeURIComponent(r.company.name)}`} className="font-semibold text-gray-100 hover:text-violet-400 transition-colors">
                        {r.company.name}
                      </Link>
                      {r.company.employee_count && (
                        <span className="ml-2 text-[11px] bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">{r.company.employee_count}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {r.company.domain && (
                        <a href={`https://${r.company.domain}`} target="_blank" rel="noopener noreferrer"
                          className="text-gray-500 hover:text-violet-400 text-xs">{r.company.domain}</a>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{r.company.industry || ""}</td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="text-xs text-gray-500 leading-relaxed truncate">
                        {r.company.lnd_evidence[0]?.slice(0, 120) || ""}
                        {(r.company.lnd_evidence[0]?.length || 0) > 120 && "..."}
                      </div>
                      {r.company.lnd_evidence.length > 1 && (
                        <span className="text-[10px] bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded mt-1 inline-block">
                          +{r.company.lnd_evidence.length - 1} more
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${confColor(r.company.confidence_score)}`}
                            style={{ width: `${r.company.confidence_score * 100}%` }} />
                        </div>
                        <span className="text-xs text-gray-500">{Math.round(r.company.confidence_score * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {r.company.sources.map((s) => (
                          <span key={s} className="text-[10px] bg-blue-950 text-blue-400 px-1.5 py-0.5 rounded font-medium">{s}</span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${r.contacts.some((c) => c.email) ? "text-emerald-400" : r.contacts.length > 0 ? "text-gray-300" : "text-gray-600"}`}>
                        {r.contacts.length}
                        {r.contacts.some((c) => c.email) && <span className="ml-1" title="Has email">&#9993;</span>}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-20 text-gray-500">
          <div className="text-5xl mb-4 opacity-50">&#128269;</div>
          <h3 className="text-lg text-gray-300 mb-2">No results found</h3>
          <p>Adjust your filters or run the scraper first.</p>
        </div>
      )}
    </>
  );
}
