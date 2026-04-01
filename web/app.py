import json
import os

from flask import Flask, render_template, request, jsonify

from models import EnrichedCompany


def create_app():
    app = Flask(__name__)

    results_path = os.path.join(os.path.dirname(__file__), "..", "data", "final", "results.json")

    def load_results() -> list[EnrichedCompany]:
        if not os.path.exists(results_path):
            return []
        with open(results_path) as f:
            data = json.load(f)
        return [EnrichedCompany.from_dict(d) for d in data]

    @app.route("/")
    def index():
        results = load_results()

        # Filters from query params
        search = request.args.get("search", "").lower()
        source_filter = request.args.get("source", "")
        has_email_only = request.args.get("has_email", "") == "1"
        confirmed_only = request.args.get("confirmed", "") == "1"
        sort_by = request.args.get("sort", "confidence")
        sort_dir = request.args.get("dir", "desc")

        if search:
            results = [r for r in results if search in r.company.name.lower()
                        or (r.company.domain and search in r.company.domain.lower())
                        or (r.company.industry and search in r.company.industry.lower())]

        if source_filter:
            results = [r for r in results if source_filter in r.company.sources]

        if has_email_only:
            results = [r for r in results if any(c.email for c in r.contacts)]

        if confirmed_only:
            results = [r for r in results if r.company.has_lnd_budget]

        # Sort
        sort_key_map = {
            "name": lambda r: r.company.name.lower(),
            "confidence": lambda r: r.company.confidence_score,
            "contacts": lambda r: len(r.contacts),
            "industry": lambda r: (r.company.industry or "").lower(),
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["confidence"])
        results.sort(key=key_fn, reverse=(sort_dir == "desc"))

        # Stats
        total = len(results)
        confirmed = sum(1 for r in results if r.company.has_lnd_budget)
        with_contacts = sum(1 for r in results if r.contacts)
        with_email = sum(1 for r in results if any(c.email for c in r.contacts))
        total_contacts = sum(len(r.contacts) for r in results)

        # All unique sources
        all_sources = sorted(set(
            s for r in load_results() for s in r.company.sources
        ))

        return render_template("index.html",
            results=results,
            stats={"total": total, "confirmed": confirmed, "with_contacts": with_contacts,
                   "with_email": with_email, "total_contacts": total_contacts},
            filters={"search": request.args.get("search", ""), "source": source_filter,
                     "has_email": has_email_only, "confirmed": confirmed_only,
                     "sort": sort_by, "dir": sort_dir},
            all_sources=all_sources,
        )

    @app.route("/company/<path:name>")
    def company_detail(name: str):
        results = load_results()
        match = None
        for r in results:
            if r.company.name == name or r.company.normalized_name == name:
                match = r
                break

        if not match:
            return "Company not found", 404

        return render_template("company.html", result=match)

    @app.route("/api/results")
    def api_results():
        results = load_results()
        return jsonify([r.to_dict() for r in results])

    return app
