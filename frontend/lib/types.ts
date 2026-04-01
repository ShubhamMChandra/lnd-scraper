export interface Contact {
  company_name: string;
  company_domain: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  title: string | null;
  email: string | null;
  email_confidence: number | null;
  linkedin_url: string | null;
  phone: string | null;
  source: string | null;
}

export interface Company {
  name: string;
  domain: string | null;
  industry: string | null;
  employee_count: string | null;
  headquarters_city: string;
  address: string | null;
  has_lnd_budget: boolean;
  lnd_evidence: string[];
  lnd_source_urls: string[];
  benefits_summary: string | null;
  sources: string[];
  confidence_score: number;
  last_updated: string;
  normalized_name: string;
}

export interface EnrichedCompany {
  company: Company;
  contacts: Contact[];
}
