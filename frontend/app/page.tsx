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
  const [sortBy, setSortBy] = useState("emails");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [confirmedOnly, setConfirmedOnly] = useState(false);
  const [hasEmailOnly, setHasEmailOnly] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

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
    const fn = sortFns[sortBy] || sortFns.emails;
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

  const copyEmail = useCallback((email: string) => {
    navigator.clipboard.writeText(email).catch(() => {});
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  }, []);

  const copyAllEmails = useCallback(() => {
    const emails = filtered
      .flatMap((r) => r.contacts.filter((c) => c.email).map((c) => c.email!))
    navigator.clipboard.writeText(emails.join("; ")).catch(() => {});
    setCopiedEmail("__all__");
    setTimeout(() => setCopiedEmail(null), 2000);
  }, [filtered]);

  const resetFilters = useCallback(() => {
    setSearch("");
    setSource("");
    setConfirmedOnly(false);
    setHasEmailOnly(false);
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
    setExportStatus(`Exported ${rows.length - 1} contacts`);
    setTimeout(() => setExportStatus(null), 3000);
  };

  return (
    <>
      {/* Screen reader announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {filtered.length} companies found
      </div>

      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          Chicago L&D Companies
        </h1>
        <p className="text-sm text-gray-500 mt-1.5 max-w-xl">
          Mid-market companies with Learning & Development budgets and HR decision-maker contacts.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="relative overflow-hidden bg-gradient-to-br from-emerald-950/50 to-emerald-950/20 border border-emerald-800/30 rounded-2xl p-5 group hover:border-emerald-700/40 transition-colors">
          <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 rounded-full -translate-y-1/2 translate-x-1/2" aria-hidden="true" />
          <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400 tabular-nums">{stats.totalEmails}</div>
          <div className="text-xs text-emerald-400/60 mt-1.5 font-semibold uppercase tracking-wider">Emails Found</div>
        </div>
        <div className="bg-gray-900/80 border border-white/[0.06] rounded-2xl p-5 hover:border-white/[0.1] transition-colors">
          <div className="text-3xl sm:text-4xl font-extrabold text-violet-400 tabular-nums">{stats.withEmail}</div>
          <div className="text-xs text-gray-500 mt-1.5 font-semibold uppercase tracking-wider">With Emails</div>
        </div>
        <div className="bg-gray-900/80 border border-white/[0.06] rounded-2xl p-5 hover:border-white/[0.1] transition-colors">
          <div className="text-3xl sm:text-4xl font-extrabold text-white tabular-nums">{stats.total}</div>
          <div className="text-xs text-gray-500 mt-1.5 font-semibold uppercase tracking-wider">Companies</div>
        </div>
        <div className="bg-gray-900/80 border border-white/[0.06] rounded-2xl p-5 hover:border-white/[0.1] transition-colors">
          <div className="text-3xl sm:text-4xl font-extrabold text-blue-400 tabular-nums">{stats.totalContacts}</div>
          <div className="text-xs text-gray-500 mt-1.5 font-semibold uppercase tracking-wider">Contacts</div>
        </div>
      </div>

      {/* Filters */}
      <fieldset className="bg-gray-900/60 border border-white/[0.06] rounded-2xl p-4 mb-6">
        <legend className="sr-only">Filter and sort companies</legend>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" aria-hidden="true">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M10 6.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Zm-.3 3.9a5 5 0 1 1 .7-.7l3.7 3.7-.7.7-3.7-3.7Z" fill="currentColor"/></svg>
            </span>
            <input
              type="text"
              placeholder="Search companies, contacts, emails..."
              aria-label="Search companies and contacts"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-gray-950/80 border border-white/[0.06] text-gray-100 rounded-xl pl-9 pr-3 py-2.5 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 placeholder-gray-600"
            />
          </div>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort by"
            className="bg-gray-950/80 border border-white/[0.06] text-gray-300 rounded-xl px-3 py-2.5 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">
            <option value="emails">Most Emails</option>
            <option value="confidence">Confidence</option>
            <option value="name">Name</option>
            <option value="contacts">Most Contacts</option>
          </select>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none hover:text-gray-300 transition-colors">
              <input type="checkbox" checked={hasEmailOnly} onChange={(e) => setHasEmailOnly(e.target.checked)}
                className="accent-emerald-500 w-3.5 h-3.5 rounded" />
              Has Email
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none hover:text-gray-300 transition-colors">
              <input type="checkbox" checked={confirmedOnly} onChange={(e) => setConfirmedOnly(e.target.checked)}
                className="accent-violet-500 w-3.5 h-3.5 rounded" />
              Confirmed L&D
            </label>
          </div>
          <div className="flex items-center gap-2 sm:ml-auto">
            <button onClick={copyAllEmails} aria-label="Copy all email addresses to clipboard"
              className="bg-white/[0.04] hover:bg-white/[0.08] text-gray-400 hover:text-gray-200 text-xs font-semibold px-3.5 py-2.5 rounded-xl border border-white/[0.06] transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">
              {copiedEmail === "__all__" ? "Copied!" : "Copy All Emails"}
            </button>
            <button onClick={exportCsv} aria-label="Export filtered results as CSV"
              className="bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg shadow-emerald-500/10 hover:shadow-emerald-500/20 transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">
              {exportStatus || "Export CSV"}
            </button>
          </div>
        </div>
      </fieldset>

      {/* Expand/collapse controls */}
      {filtered.length > 0 && (
        <div className="flex items-center gap-3 mb-3 px-1">
          <span className="text-xs text-gray-500 tabular-nums">{filtered.length} companies</span>
          <span className="text-gray-800" aria-hidden="true">&middot;</span>
          <button onClick={expandAll} aria-label="Expand all company details" className="text-xs text-violet-400 hover:text-violet-300 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">Expand all</button>
          <button onClick={collapseAll} aria-label="Collapse all company details" className="text-xs text-gray-500 hover:text-gray-300 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">Collapse all</button>
        </div>
      )}

      {/* Results — accordion layout */}
      {filtered.length > 0 ? (
        <div className="space-y-2" role="list">
          {filtered.map((r, idx) => {
            const emailContacts = r.contacts.filter((c) => c.email);
            const linkedinOnly = r.contacts.filter((c) => !c.email && c.linkedin_url);
            const isOpen = expanded.has(r.company.normalized_name);
            const emailCount = emailContacts.length;

            return (
              <div key={r.company.normalized_name} role="listitem" className={`bg-gray-900/60 border rounded-2xl overflow-hidden transition-all duration-200 ${isOpen ? "border-violet-500/20 shadow-lg shadow-violet-500/[0.03]" : "border-white/[0.06] hover:border-white/[0.1]"}`}>
                {/* Accordion header */}
                <button
                  id={`accordion-${idx}`}
                  onClick={() => toggleExpand(r.company.normalized_name)}
                  aria-expanded={isOpen}
                  aria-controls={`panel-${idx}`}
                  className="w-full flex items-center gap-3 sm:gap-4 px-4 py-3.5 sm:px-5 sm:py-4 text-left cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-violet-500 group"
                >
                  <span className={`text-gray-600 group-hover:text-gray-400 transition-all text-[10px] ${isOpen ? "rotate-90" : ""}`} aria-hidden="true">&#9654;</span>

                  <div className="min-w-0 flex-1">
                    <span className="font-semibold text-gray-100 group-hover:text-white transition-colors">{r.company.name}</span>
                    {r.company.domain && (
                      <span className="ml-2 text-xs text-gray-600 hidden sm:inline">{r.company.domain}</span>
                    )}
                  </div>

                  {emailCount > 0 ? (
                    <span className="bg-emerald-500/10 text-emerald-400 text-[11px] font-bold px-2.5 py-1 rounded-lg shrink-0 tabular-nums">
                      {emailCount} email{emailCount > 1 ? "s" : ""}
                    </span>
                  ) : r.contacts.length > 0 ? (
                    <span className="bg-white/[0.04] text-gray-500 text-[11px] px-2.5 py-1 rounded-lg shrink-0 tabular-nums">
                      {r.contacts.length} contact{r.contacts.length > 1 ? "s" : ""}
                    </span>
                  ) : (
                    <span className="text-[11px] text-gray-700 shrink-0">no contacts</span>
                  )}

                  {!isOpen && emailCount > 0 && (
                    <span className="text-xs text-emerald-500/70 truncate max-w-xs hidden lg:inline font-mono">
                      {emailContacts[0].email}
                      {emailCount > 1 && <span className="text-gray-600 ml-1">+{emailCount - 1}</span>}
                    </span>
                  )}

                  <div className="flex items-center gap-2 shrink-0" title={`${Math.round(r.company.confidence_score * 100)}% confidence`}>
                    <div className="w-10 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${r.company.confidence_score >= 0.7 ? "bg-emerald-500" : r.company.confidence_score >= 0.4 ? "bg-amber-500" : "bg-red-400"}`}
                        style={{ width: `${r.company.confidence_score * 100}%` }} />
                    </div>
                    <span className="text-[11px] text-gray-600 w-7 tabular-nums">{Math.round(r.company.confidence_score * 100)}%</span>
                  </div>
                </button>

                {/* Accordion body */}
                {isOpen && (
                  <div id={`panel-${idx}`} role="region" aria-labelledby={`accordion-${idx}`} className="px-4 pb-4 sm:px-5 border-t border-white/[0.04]">
                    <div className="flex items-center gap-3 pt-3 pb-3">
                      <Link href={`/company/${encodeURIComponent(r.company.name)}`}
                        className="text-xs text-violet-400 hover:text-violet-300 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">
                        View details &rarr;
                      </Link>
                      <div className="flex gap-1.5 ml-auto">
                        {r.company.sources.map((s) => (
                          <span key={s} className="text-[10px] bg-blue-500/[0.08] text-blue-400/80 px-2 py-0.5 rounded-md font-medium">{s}</span>
                        ))}
                      </div>
                    </div>

                    {emailContacts.length > 0 && (
                      <div className="bg-emerald-950/20 border border-emerald-500/10 rounded-xl p-3.5 mb-3">
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {emailContacts.map((c, i) => (
                            <div key={i} className="flex items-start gap-2.5 group/card">
                              <span className="flex items-center justify-center w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-400 text-xs mt-0.5 shrink-0" aria-hidden="true">&#9993;</span>
                              <div className="min-w-0 flex-1">
                                <button
                                  onClick={() => copyEmail(c.email!)}
                                  className="text-sm text-emerald-300 hover:text-emerald-200 font-medium break-all text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 transition-colors"
                                  title="Click to copy email"
                                  aria-label={`Copy email ${c.email} to clipboard`}
                                >
                                  {copiedEmail === c.email ? (
                                    <span className="text-green-400">Copied!</span>
                                  ) : (
                                    c.email
                                  )}
                                </button>
                                <div className="text-[11px] text-gray-500 truncate mt-0.5">
                                  {c.full_name}{c.title ? ` — ${c.title}` : ""}
                                </div>
                                {c.email_confidence != null && (
                                  <span className={`text-[10px] font-semibold ${c.email_confidence >= 0.8 ? "text-emerald-500/80" : c.email_confidence >= 0.5 ? "text-amber-500/80" : "text-red-400/80"}`}
                                    title="Confidence that this email address is valid">
                                    {Math.round(c.email_confidence * 100)}% conf
                                  </span>
                                )}
                              </div>
                              {c.linkedin_url && (
                                <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                                  aria-label={`${c.full_name} LinkedIn profile`}
                                  className="text-[10px] text-blue-400/60 hover:text-blue-400 shrink-0 font-bold bg-blue-500/[0.08] px-1.5 py-0.5 rounded transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">in</a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {linkedinOnly.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {linkedinOnly.map((c, i) => (
                          <a key={i} href={c.linkedin_url || "#"} target="_blank" rel="noopener noreferrer"
                            className="text-[11px] text-gray-500 hover:text-blue-400 bg-white/[0.03] hover:bg-blue-500/[0.08] px-2.5 py-1.5 rounded-lg transition-all border border-transparent hover:border-blue-500/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500">
                            <span className="font-bold mr-1 text-blue-400/50">in</span>{c.full_name}
                          </a>
                        ))}
                      </div>
                    )}

                    {r.contacts.length === 0 && (
                      <div className="text-xs text-gray-600 italic pt-1">No contacts found yet</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-24 text-gray-400">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-gray-900 border border-white/[0.06] flex items-center justify-center">
            <svg width="28" height="28" viewBox="0 0 15 15" fill="none" className="text-gray-600"><path d="M10 6.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Zm-.3 3.9a5 5 0 1 1 .7-.7l3.7 3.7-.7.7-3.7-3.7Z" fill="currentColor"/></svg>
          </div>
          <h3 className="text-base font-semibold text-gray-300 mb-2">No results found</h3>
          <p className="mb-5 text-sm text-gray-500">
            {search ? "Your search didn't match any companies." : "All companies have been filtered out."}
          </p>
          <button onClick={resetFilters}
            className="text-violet-400 hover:text-violet-300 font-semibold text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 transition-colors">
            Reset all filters
          </button>
        </div>
      )}
    </>
  );
}
