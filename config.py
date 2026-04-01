import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "serpapi_key": os.getenv("SERPAPI_KEY"),
    "apollo_api_key": os.getenv("APOLLO_API_KEY"),
    "hunter_api_key": os.getenv("HUNTER_API_KEY"),

    "output_dir": os.path.join(os.path.dirname(__file__), "data", "final"),
    "raw_dir": os.path.join(os.path.dirname(__file__), "data", "raw"),

    "scrapers": {
        "builtin": {"enabled": True, "rate_limit": 3.0},
        "serpapi_google": {"enabled": True, "rate_limit": 1.0},
        "serpapi_jobs": {"enabled": True, "rate_limit": 1.0},
        "glassdoor": {"enabled": True, "rate_limit": 1.0},
        "crains": {"enabled": True, "rate_limit": 3.0},
        "greatplacetowork": {"enabled": True, "rate_limit": 3.0},
        "career_pages": {"enabled": True, "rate_limit": 3.0},
    },

    "enrichment": {
        "apollo": {"enabled": True, "max_credits": 2000},
        "hunter": {"enabled": True, "max_credits": 50},
        "google_search": {"enabled": True, "max_searches": 50},
        "website_team": {"enabled": True},
    },

    "dedup": {
        "fuzzy_threshold": 85,
    },
}
