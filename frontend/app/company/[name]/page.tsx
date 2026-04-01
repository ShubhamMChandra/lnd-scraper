import Link from "next/link";
import { EnrichedCompany } from "@/lib/types";
import resultsData from "@/lib/results.json";
import { notFound } from "next/navigation";

const results = resultsData as EnrichedCompany[];

export function generateStaticParams() {
  return results.map((r) => ({ name: encodeURIComponent(r.company.name) }));
}

export default async function CompanyPage({ params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  const decodedName = decodeURIComponent(name);
  const result = results.find(
    (r) => r.company.name === decodedName || r.company.normalized_name === decodedName
  );

  if (!result) return notFound();

  const { company, contacts } = result;
  const confBar = company.confidence_score >= 0.7 ? "bg-emerald-500" : company.confidence_score >= 0.4 ? "bg-amber-500" : "bg-red-400";

  return (
    <>
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-6 inline-flex items-center gap-1.5 group focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 rounded">
        <span className="group-hover:-translate-x-0.5 transition-transform">&larr;</span> Back to all companies
      </Link>

      <div className="mb-8">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{company.name}</h1>
          <span className={`text-[11px] font-semibold px-3 py-1 rounded-lg ${company.has_lnd_budget ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"}`}>
            {company.has_lnd_budget ? "Confirmed L&D" : "Unconfirmed"}
          </span>
        </div>
        {company.domain && (
          <a href={`https://${company.domain}`} target="_blank" rel="noopener noreferrer"
            className="text-gray-500 hover:text-violet-400 text-sm mt-1.5 inline-flex items-center gap-1 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 rounded">
            {company.domain} <span className="text-xs">&#8599;</span>
          </a>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-6">
        {/* Company Info */}
        <div className="bg-gray-900/60 border border-white/[0.06] rounded-2xl p-6">
          <h2 className="text-sm font-semibold mb-4 pb-3 border-b border-white/[0.06] text-gray-300 uppercase tracking-wider">Company Info</h2>
          <dl className="space-y-3.5">
            {company.industry && (
              <div className="flex gap-4">
                <dt className="text-xs text-gray-600 min-w-[90px] font-medium">Industry</dt>
                <dd className="text-sm text-gray-200">{company.industry}</dd>
              </div>
            )}
            {company.employee_count && (
              <div className="flex gap-4">
                <dt className="text-xs text-gray-600 min-w-[90px] font-medium">Size</dt>
                <dd className="text-sm text-gray-200">{company.employee_count}</dd>
              </div>
            )}
            <div className="flex gap-4">
              <dt className="text-xs text-gray-600 min-w-[90px] font-medium">Location</dt>
              <dd className="text-sm text-gray-200">{company.headquarters_city}</dd>
            </div>
            <div className="flex gap-4">
              <dt className="text-xs text-gray-600 min-w-[90px] font-medium">Confidence</dt>
              <dd className="text-sm flex items-center gap-2.5">
                <div className="w-28 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${confBar}`} style={{ width: `${company.confidence_score * 100}%` }} />
                </div>
                <span className="tabular-nums text-gray-300">{Math.round(company.confidence_score * 100)}%</span>
              </dd>
            </div>
            <div className="flex gap-4">
              <dt className="text-xs text-gray-600 min-w-[90px] font-medium">Sources</dt>
              <dd className="flex flex-wrap gap-1.5">
                {company.sources.map((s) => (
                  <span key={s} className="text-[10px] bg-blue-500/[0.08] text-blue-400/80 px-2 py-0.5 rounded-md font-medium">{s}</span>
                ))}
              </dd>
            </div>
          </dl>
        </div>

        {/* L&D Evidence */}
        <div className="bg-gray-900/60 border border-white/[0.06] rounded-2xl p-6">
          <h2 className="text-sm font-semibold mb-4 pb-3 border-b border-white/[0.06] text-gray-300 uppercase tracking-wider">L&D Evidence</h2>
          {company.lnd_evidence.length > 0 ? (
            <ul className="space-y-2.5">
              {company.lnd_evidence.map((e, i) => (
                <li key={i} className="text-xs text-gray-400 leading-relaxed bg-violet-500/[0.04] p-3.5 rounded-xl border-l-[3px] border-l-violet-500/40">
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600 italic">No specific evidence collected yet.</p>
          )}

          {company.lnd_source_urls.length > 0 && (
            <>
              <h3 className="text-[11px] font-semibold text-gray-500 mt-5 mb-2 uppercase tracking-wider">Source URLs</h3>
              <ul className="space-y-1.5">
                {company.lnd_source_urls.map((url, i) => (
                  <li key={i}>
                    <a href={url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-violet-400/80 hover:text-violet-300 break-all transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 rounded">{url.slice(0, 80)}{url.length > 80 && "..."}</a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Contacts */}
      <div className="bg-gray-900/60 border border-white/[0.06] rounded-2xl p-6">
        <h2 className="text-sm font-semibold mb-4 pb-3 border-b border-white/[0.06] text-gray-300 uppercase tracking-wider">
          HR Contacts <span className="text-gray-600 font-normal">({contacts.length})</span>
        </h2>
        {contacts.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {contacts.map((c, i) => (
              <div key={i} className="bg-gray-950/50 border border-white/[0.04] rounded-xl p-4 hover:border-white/[0.08] transition-all group">
                <div className="font-semibold text-sm text-gray-100">{c.full_name || "Unknown"}</div>
                {c.title && <div className="text-xs text-gray-500 mt-0.5">{c.title}</div>}
                <div className="mt-3 space-y-2">
                  {c.email && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="flex items-center justify-center w-5 h-5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]" aria-hidden="true">&#9993;</span>
                      <a href={`mailto:${c.email}`} className="text-emerald-400 hover:text-emerald-300 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 rounded">{c.email}</a>
                      {c.email_confidence != null && (
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md ${c.email_confidence >= 0.8 ? "bg-emerald-500/10 text-emerald-400/80" : c.email_confidence >= 0.5 ? "bg-amber-500/10 text-amber-400/80" : "bg-red-500/10 text-red-400/80"}`}>
                          {Math.round(c.email_confidence * 100)}%
                        </span>
                      )}
                    </div>
                  )}
                  {c.linkedin_url && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="flex items-center justify-center w-5 h-5 rounded bg-blue-500/[0.08] text-blue-400/80 text-[10px] font-bold" aria-hidden="true">in</span>
                      <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                        className="text-blue-400/80 hover:text-blue-300 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 rounded">LinkedIn Profile</a>
                    </div>
                  )}
                  {c.phone && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="flex items-center justify-center w-5 h-5 rounded bg-white/[0.04] text-gray-500 text-[10px]" aria-hidden="true">&#9742;</span>
                      <span className="text-gray-400">{c.phone}</span>
                    </div>
                  )}
                </div>
                <div className="mt-3 text-[10px] text-gray-600 font-medium uppercase tracking-wider">via {c.source}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-600 py-8 text-sm">No HR contacts found for this company.</p>
        )}
      </div>
    </>
  );
}
