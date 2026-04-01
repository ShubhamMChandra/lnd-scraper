"use client";

import { useState, useMemo, useCallback } from "react";
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
  const [hasEmailOnly, setHasEmailOnly] = useState(true); // default ON
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const allSources = useMemo(() => getAllSources(results), []);

  const filtered = useMemo(() => {
    let data = [...results];
    const q = search.toLowerCase();
    if (q) {
      data = data.filter(
        (r) =>
          r.company.name.toLowerCase().includes(q) ||
          (r.company.domain && r.company.domain.toLowerCase().includes(q)) ||
          (r.company.industry && r.company.industry.toLowerCase().includes(q)) ||
          r.contacts.some((c) => c.full_name?.toLowerCase().includes(q) || c.email?.toLowerCase().includes(q))
      );
    }
    if (source) data = data.filter((r) => r.company.sources.includes(source));
    if (confirmedOnly) data = data.filter((r) => r.company.has_lnd_budget);
    if (hasEmailOnly) data = data.filter((r) => r.contacts.some((c) => c.email));

    const sortFns: Record<string, (a: EnrichedCompany, b: EnrichedCompany) => number> = {
      confidence: (a, b) => a.company.confidence_score - b.company.confidence_score,
      name: (a, b) => a.company.name.localeCompare(b.company.name),
      contacts: (a, b) => a.contacts.length - b.contacts.length,
      emails: (a, b) => a.contacts.filter((c) => c.email).length - b.contacts.filter((c) => c.email).length,
    };
    const fn = sortFns[sortBy] || sortFns.confidence;
    data.sort((a, b) => (sortDir === "desc" ? -fn(a, b) : fn(a, b)));
    return data;
  }, [search, source, sortBy, sortDir, confirmedOnly, hasEmailOnly]);

  const toggleExpand = useCallback((name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpanded(new Set(filtered.map((r) => r.company.normalized_name)));
  }, [filtered]);

  const collapseAll = useCallback(() => {
    setExpanded(new Set());
  }, []);

  const stats = useMemo(() => ({
    total: results.length,
    withEmail: results.filter((r) => r.contacts.some((c) => c.email)).length,
    totalEmails: results.reduce((sum, r) => sum + r.contacts.filter((c) => c.email).length, 0),
    withContacts: results.filter((r) => r.contacts.length > 0).length,
    totalContacts: results.reduce((sum, r) => sum + r.contacts.length, 0),
  }), []);

  const exportCsv = () => {
    const rows = [
      ["Company", "Domain", "Contact Name", "Title", "Email", "LinkedIn", "Confidence", "Source"].join(","),
    ];
    filtered.forEach((r) => {
      const emailContacts = r.contacts.filter((c) => c.email);
      const contactsToExport = emailContacts.length > 0 ? emailContacts : r.contacts;
      contactsToExport.forEach((c) => {
        rows.push([
          `"${r.company.name}"`, r.company.domain || "",
          `"${c.full_name || ""}"`, `"${c.title || ""}"`,
          c.email || "", c.linkedin_url || "",
          `${Math.round(r.company.confidence_score * 100)}%`,
          c.source || "",
        ].join(","));
      });
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lnd_contacts.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* Stats — emails front and center */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:-translate-y-0.5 transition-transform">
          <div className="text-3xl font-bold text-emerald-400">{stats.totalEmails}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium">Emails Found</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:-translate-y-0.5 transition-transform">
          <div className="text-3xl font-bold text-violet-400">{stats.withEmail}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium">Companies w/ Email</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:-translate-y-0.5 transition-transform">
          <div className="text-3xl font-bold text-white">{stats.total}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium">Total Companies</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:-translate-y-0.5 transition-transform">
          <div className="text-3xl font-bold text-blue-400">{stats.totalContacts}</div>
          <div className="text-xs text-gray-500 mt-1 font-medium">Total Contacts</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search companies, contacts, emails..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm w-72 focus:outline-none focus:border-violet-500 placeholder-gray-600"
          />
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
            className="bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-violet-500">
            <option value="emails">Most Emails</option>
            <option value="confidence">Confidence</option>
            <option value="name">Name</option>
            <option value="contacts">Most Contacts</option>
          </select>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
            <input type="checkbox" checked={hasEmailOnly} onChange={(e) => setHasEmailOnly(e.target.checked)}
              className="accent-emerald-500 w-3.5 h-3.5" />
            Has Email Only
          </label>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
            <input type="checkbox" checked={confirmedOnly} onChange={(e) => setConfirmedOnly(e.target.checked)}
              className="accent-violet-500 w-3.5 h-3.5" />
            Confirmed L&D
          </label>
          <button onClick={exportCsv}
            className="ml-auto bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
            Export Contacts CSV
          </button>
        </div>
      </div>

      {/* Expand/collapse controls */}
      {filtered.length > 0 && (
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs text-gray-500">{filtered.length} companies</span>
          <button onClick={expandAll} className="text-xs text-violet-400 hover:text-violet-300 transition-colors">Expand all</button>
          <button onClick={collapseAll} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Collapse all</button>
        </div>
      )}

      {/* Results — accordion layout */}
      {filtered.length > 0 ? (
        <div className="space-y-2">
          {filtered.map((r) => {
            const emailContacts = r.contacts.filter((c) => c.email);
            const linkedinOnly = r.contacts.filter((c) => !c.email && c.linkedin_url);
            const isOpen = expanded.has(r.company.normalized_name);
            const emailCount = emailContacts.length;

            return (
              <div key={r.company.normalized_name} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-colors">
                {/* Accordion header — always visible */}
                <button
                  onClick={() => toggleExpand(r.company.normalized_name)}
                  className="w-full flex items-center gap-4 px-5 py-4 text-left cursor-pointer"
                >
                  {/* Expand arrow */}
                  <span className={`text-gray-500 transition-transform ${isOpen ? "rotate-90" : ""}`}>&#9654;</span>

                  {/* Company name */}
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold text-gray-100">{r.company.name}</span>
                    {r.company.domain && (
                      <span className="ml-2 text-xs text-gray-600">{r.company.domain}</span>
                    )}
                  </div>

                  {/* Email count badge — prominent */}
                  {emailCount > 0 ? (
                    <span className="bg-emerald-500/15 text-emerald-400 text-xs font-bold px-2.5 py-1 rounded-full shrink-0">
                      {emailCount} email{emailCount > 1 ? "s" : ""}
                    </span>
                  ) : r.contacts.length > 0 ? (
                    <span className="bg-gray-800 text-gray-500 text-xs px-2.5 py-1 rounded-full shrink-0">
                      {r.contacts.length} contact{r.contacts.length > 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-700 shrink-0">no contacts</span>
                  )}

                  {/* Quick email preview on collapsed */}
                  {!isOpen && emailCount > 0 && (
                    <span className="text-xs text-emerald-400/70 truncate max-w-xs hidden md:inline">
                      {emailContacts[0].email}
                      {emailCount > 1 && ` +${emailCount - 1}`}
                    </span>
                  )}

                  {/* Confidence */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${r.company.confidence_score >= 0.7 ? "bg-emerald-500" : r.company.confidence_score >= 0.4 ? "bg-amber-500" : "bg-red-400"}`}
                        style={{ width: `${r.company.confidence_score * 100}%` }} />
                    </div>
                    <span className="text-[11px] text-gray-600 w-7">{Math.round(r.company.confidence_score * 100)}%</span>
                  </div>
                </button>

                {/* Accordion body — contacts */}
                {isOpen && (
                  <div className="px-5 pb-4 border-t border-gray-800/50">
                    <div className="flex items-center gap-3 pt-3 pb-2">
                      <Link href={`/company/${encodeURIComponent(r.company.name)}`}
                        className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
                        View full details &rarr;
                      </Link>
                      {r.company.sources.map((s) => (
                        <span key={s} className="text-[10px] bg-blue-950 text-blue-400 px-1.5 py-0.5 rounded font-medium">{s}</span>
                      ))}
                    </div>

                    {/* Emails */}
                    {emailContacts.length > 0 && (
                      <div className="bg-emerald-950/30 border border-emerald-900/40 rounded-lg p-3 mb-3">
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {emailContacts.map((c, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <span className="text-emerald-400 text-sm mt-0.5">&#9993;</span>
                              <div className="min-w-0 flex-1">
                                <a href={`mailto:${c.email}`} className="text-sm text-emerald-300 hover:text-emerald-200 font-medium break-all">
                                  {c.email}
                                </a>
                                <div className="text-[11px] text-gray-500 truncate">
                                  {c.full_name}{c.title ? ` — ${c.title}` : ""}
                                </div>
                                {c.email_confidence != null && (
                                  <span className={`text-[10px] font-medium ${c.email_confidence >= 0.8 ? "text-emerald-500" : c.email_confidence >= 0.5 ? "text-amber-500" : "text-red-400"}`}>
                                    {Math.round(c.email_confidence * 100)}% confidence
                                  </span>
                                )}
                              </div>
                              {c.linkedin_url && (
                                <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                                  className="text-xs text-blue-400 hover:text-blue-300 shrink-0 font-bold">in</a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* LinkedIn-only */}
                    {linkedinOnly.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {linkedinOnly.map((c, i) => (
                          <a key={i} href={c.linkedin_url || "#"} target="_blank" rel="noopener noreferrer"
                            className="text-[11px] text-gray-500 hover:text-blue-400 bg-gray-800 px-2 py-1 rounded transition-colors">
                            <span className="font-bold mr-1">in</span>{c.full_name}
                          </a>
                        ))}
                      </div>
                    )}

                    {r.contacts.length === 0 && (
                      <div className="text-xs text-gray-600 italic pt-2">No contacts found yet</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-20 text-gray-500">
          <div className="text-5xl mb-4 opacity-50">&#128269;</div>
          <h3 className="text-lg text-gray-300 mb-2">No results found</h3>
          <p>Adjust your filters or uncheck &quot;Has Email Only&quot;.</p>
        </div>
      )}
    </>
  );
}
