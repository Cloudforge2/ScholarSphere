from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from .core import (
    fetch_semantic_scholar_author,
    fetch_semantic_scholar_papers,
    search_openalex_authors_by_name,
    fetch_openalex_papers,
    merge_papers,
    generate_author_summary
)
import uvicorn

app = FastAPI(title="Author Summary Service")

# Match the query parameter from the gateway
@app.get("/professors/summary/by-name")
def author_summary(name: str = Query(..., description="Author name")):
    author = name  # map to internal variable
    try:
        ss_authors = fetch_semantic_scholar_author(author)
        if not ss_authors:
            return JSONResponse({"error": "No authors found in Semantic Scholar."}, status_code=404)

        selected_author = ss_authors[0]
        author_id = selected_author.get("authorId")
        author_name = selected_author.get("name", "Unknown")
        affiliations = selected_author.get("affiliations", [])

        ss_papers = fetch_semantic_scholar_papers(author_id)
        openalex_authors = search_openalex_authors_by_name(author)
        openalex_papers = []

        if openalex_authors:
            numeric_id = openalex_authors[0].get("id", "").split("/")[-1]
            openalex_papers = fetch_openalex_papers(numeric_id)

        papers = merge_papers(openalex_papers, ss_papers)
        if not papers:
            return JSONResponse({"error": "No papers found for author."}, status_code=404)

        summary = generate_author_summary(author_name, papers, affiliations)

        return {
            "author": author_name,
            "affiliations": affiliations,
            "summary": summary,
            "papers": papers
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
