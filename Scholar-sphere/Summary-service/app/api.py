from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from typing import List, Dict
from .core import (
    fetch_semantic_scholar_author,
    fetch_semantic_scholar_papers,
    fetch_openalex_authors,
    fetch_openalex_papers,
    generate_research_summary,
    extract_research_themes,
)
import uvicorn

app = FastAPI(title="Author Profile Service")


def merge_papers(openalex_papers: List[Dict], ss_papers: List[Dict]) -> List[Dict]:
    """Merge and deduplicate papers by title (case-insensitive)"""
    combined = {p["title"].strip().lower(): p for p in (openalex_papers + ss_papers) if p.get("title")}
    return list(combined.values())


@app.get("/professors/summary/by-name")
def author_profile(name: str = Query(..., min_length=1, description="Author name")):
    try:
        # --- Fetch OpenAlex authors ---
        oa_authors = fetch_openalex_authors(name)
        if not oa_authors:
            return JSONResponse({"error": "No authors found on OpenAlex."}, status_code=404)

        # Pick author with most papers
        oa_author = max(oa_authors, key=lambda a: a.get("works_count", 0))
        author_name = oa_author.get("display_name", name)
        author_id = oa_author.get("id", "").split("/")[-1]

        # --- Fetch OpenAlex papers ---
        oa_papers = fetch_openalex_papers(author_id, author_name)

        # --- Semantic Scholar fallback ---
        ss_papers = []
        ss_authors = fetch_semantic_scholar_author(name)
        if ss_authors:
            ss_best = max(ss_authors, key=lambda a: a.get("paperCount", 0))
            ss_papers = fetch_semantic_scholar_papers(ss_best["authorId"], author_name)

        # Merge and deduplicate papers
        all_papers = merge_papers(oa_papers, ss_papers)
        if not all_papers:
            return JSONResponse({"error": "No papers found for author."}, status_code=404)

        # --- Generate research summary ---
        summary = generate_research_summary(all_papers, author_name)

        # --- Extract key research areas ---
        papers_with_abstracts = [p for p in all_papers if p.get("abstract") and len(p["abstract"]) > 50]
        key_research_areas = extract_research_themes(papers_with_abstracts)[:8]

        # --- Extract affiliation ---
        affiliation = "Unknown"
        last_known_inst = oa_author.get("last_known_institutions")
        if last_known_inst and isinstance(last_known_inst, list) and len(last_known_inst) > 0:
            affiliation = last_known_inst[0].get("display_name", "Unknown")
        elif oa_author.get("last_known_institution"):
            inst = oa_author.get("last_known_institution")
            if isinstance(inst, dict):
                affiliation = inst.get("display_name", "Unknown")

        profile = {
            "author": author_name,
            "affiliation": affiliation,
            "total_publications": oa_author.get("works_count", "N/A"),
            "citation_count": oa_author.get("cited_by_count", "N/A"),
            "h_index": oa_author.get("summary_stats", {}).get("h_index", "N/A"),
            "summary": summary,
            "key_research_areas": key_research_areas
        }

        return profile

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/papers/by-title")
def get_paper_abstract(
    author_name: str = Query(..., description="Full author name"),
    paper_title: str = Query(..., description="Exact or partial paper title")
):
    """
    Return abstract of a paper by matching title under the given author.
    """
    try:
        # --- Fetch OpenAlex authors ---
        oa_authors = fetch_openalex_authors(author_name)
        if not oa_authors:
            return JSONResponse({"error": "Author not found on OpenAlex."}, status_code=404)

        # Pick author with most papers
        oa_author = max(oa_authors, key=lambda a: a.get("works_count", 0))
        author_display_name = oa_author.get("display_name", author_name)
        author_id = oa_author.get("id", "").split("/")[-1]

        # --- Fetch Papers ---
        oa_papers = fetch_openalex_papers(author_id, author_display_name)

        ss_papers = []
        ss_authors = fetch_semantic_scholar_author(author_name)
        if ss_authors:
            ss_best = max(ss_authors, key=lambda a: a.get("paperCount", 0))
            ss_papers = fetch_semantic_scholar_papers(ss_best["authorId"], author_display_name)

        # Merge papers
        all_papers = merge_papers(oa_papers, ss_papers)

        if not all_papers:
            return JSONResponse({"error": "No papers found for this author."}, status_code=404)

        # --- Search for paper title ---
        paper_title_lower = paper_title.strip().lower()
        for p in all_papers:
            if paper_title_lower in p.get("title", "").lower():
                return {
                    "title": p.get("title"),
                    "abstract": p.get("abstract", "Abstract not available"),
                    "venue": p.get("venue"),
                    "year": p.get("year"),
                    "citations": p.get("citations"),
                    "source": p.get("source")
                }

        return JSONResponse({"error": "Paper title not found for this author."}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
