"""Shared test fixtures and mock data."""

OA_RESPONSE = {
    "results": [
        {
            "title": "Attention Is All You Need",
            "publication_year": 2017,
            "authorships": [{"author": {"display_name": "Ashish Vaswani"}}],
            "primary_location": {"source": {"display_name": "NeurIPS"}},
            "doi": "https://doi.org/10.48550/arxiv.1706.03762",
        }
    ]
}

OA_EMPTY_RESPONSE = {"results": []}

OA_LOW_SCORE_RESPONSE = {
    "results": [
        {
            "title": "Completely Unrelated Topic About Cooking",
            "publication_year": 2020,
            "authorships": [],
            "primary_location": {},
            "doi": "",
        }
    ]
}

CR_RESPONSE = {
    "status": "ok",
    "message": {
        "title": ["Attention Is All You Need"],
        "published-print": {"date-parts": [[2017]]},
        "author": [{"family": "Vaswani", "given": "Ashish"}],
        "container-title": ["Advances in Neural Information Processing Systems"],
    },
}

CR_NOT_FOUND = None
