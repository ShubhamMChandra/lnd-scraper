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
  const confClass = company.confidence_score >= 0.7 ? "bg-emerald-500/10 text-emerald-400" : company.confidence_score >= 0.4 ? "bg-amber-500/10 text-amber-400" : "bg-red-500/10 text-red-400";
  const confBar = company.confidence_score >= 0.7 ? "bg-emerald-500" : company.confidence_score >= 0.4 ? "bg-amber-500" : "bg-red-400";

  return (
    <>
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-5 inline-block">
        &larr; Back to all companies
      </Link>

      <div className="mb-7">
        <div className="flex items-center gap-4 flex-wrap">
          <h1 className="text-3xl font-bold">{company.name}</h1>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full ${company.has_lnd_budget ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
            {company.has_lnd_budget ? "Confirmed L&D" : "Unconfirmed"}
          </span>
        </div>
        {company.domain && (
          <a href={`https://${company.domain}`} target="_blank" rel="noopener noreferrer"
            className="text-gray-500 hover:text-violet-400 text-sm mt-1 inline-block">
            {company.domain} &#8599;
          </a>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-5 mb-6">
        {/* Company Info */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 pb-3 border-b border-gray-800">Company Info</h2>
          <dl className="space-y-3">
            {company.industry && (
              <div className="flex gap-4">
                <dt className="text-xs text-gray-500 min-w-[90px] font-medium">Industry</dt>
                <dd className="text-sm">{company.industry}</dd>
              </div>
            )}
            {company.employee_count && (
              <div className="flex gap-4">
                <dt className="text-xs text-gray-500 min-w-[90px] font-medium">Size</dt>
                <dd className="text-sm">{company.employee_count}</dd>
              </div>
            )}
            <div className="flex gap-4">
              <dt className="text-xs text-gray-500 min-w-[90px] font-medium">Location</dt>
              <dd className="text-sm">{company.headquarters_city}</dd>
            </div>
            <div className="flex gap-4">
              <dt className="text-xs text-gray-500 min-w-[90px] font-medium">Confidence</dt>
              <dd className="text-sm flex items-center gap-2">
                <div className="w-28 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${confBar}`} style={{ width: `${company.confidence_score * 100}%` }} />
                </div>
                <span>{Math.round(company.confidence_score * 100)}%</span>
              </dd>
            </div>
            <div className="flex gap-4">
              <dt className="text-xs text-gray-500 min-w-[90px] font-medium">Sources</dt>
              <dd className="flex flex-wrap gap-1">
                {company.sources.map((s) => (
                  <span key={s} className="text-[10px] bg-blue-950 text-blue-400 px-1.5 py-0.5 rounded font-medium">{s}</span>
                ))}
              </dd>
            </div>
          </dl>
        </div>

        {/* L&D Evidence */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 pb-3 border-b border-gray-800">L&D Evidence</h2>
          {company.lnd_evidence.length > 0 ? (
            <ul className="space-y-2.5">
              {company.lnd_evidence.map((e, i) => (
                <li key={i} className="text-xs text-gray-400 leading-relaxed bg-gray-950/50 p-3 rounded-lg border-l-3 border-l-violet-500">
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600 italic">No specific evidence collected yet.</p>
          )}

          {company.lnd_source_urls.length > 0 && (
            <>
              <h3 className="text-xs font-semibold text-gray-500 mt-5 mb-2">Source URLs</h3>
              <ul className="space-y-1.5">
                {company.lnd_source_urls.map((url, i) => (
                  <li key={i}>
                    <a href={url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-violet-400 hover:text-violet-300 break-all">{url.slice(0, 80)}{url.length > 80 && "..."}</a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Contacts */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-base font-semibold mb-4 pb-3 border-b border-gray-800">
          HR Contacts ({contacts.length})
        </h2>
        {contacts.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {contacts.map((c, i) => (
              <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors">
                <div className="font-semibold text-sm">{c.full_name || "Unknown"}</div>
                {c.title && <div className="text-xs text-gray-500 mt-0.5">{c.title}</div>}
                <div className="mt-3 space-y-2">
                  {c.email && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600 w-4 text-center">&#9993;</span>
                      <a href={`mailto:${c.email}`} className="text-violet-400 hover:text-violet-300">{c.email}</a>
                      {c.email_confidence != null && (
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${c.email_confidence >= 0.8 ? "bg-emerald-500/10 text-emerald-400" : c.email_confidence >= 0.5 ? "bg-amber-500/10 text-amber-400" : "bg-red-500/10 text-red-400"}`}>
                          {Math.round(c.email_confidence * 100)}%
                        </span>
                      )}
                    </div>
                  )}
                  {c.linkedin_url && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600 w-4 text-center font-bold">in</span>
                      <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                        className="text-violet-400 hover:text-violet-300">LinkedIn Profile</a>
                    </div>
                  )}
                  {c.phone && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600 w-4 text-center">&#9742;</span>
                      <span>{c.phone}</span>
                    </div>
                  )}
                </div>
                <div className="mt-3 text-[10px] text-gray-600 uppercase tracking-wider">via {c.source}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-gray-600 py-8">No HR contacts found for this company.</p>
        )}
      </div>
    </>
  );
}
