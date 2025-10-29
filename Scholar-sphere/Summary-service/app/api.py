import asyncio
from fastapi import FastAPI, Query, HTTPException
from urllib.parse import unquote
import aiohttp
import core

app = FastAPI(
    title="Enhanced Author and Paper Summary Service",
    description="Provides advanced, multi-source, LLM-generated summaries for academic authors and papers."
)

# This matches: /professors/summary/**
# Renamed endpoint for clarity, but path is what matters for the gateway.
@app.get("/professors/summary/by-name", tags=["Professors"])
async def get_professor_summary_by_name(name: str = Query(..., description="Full name of the author")):
    """
    Generates a research summary for a professor using the advanced, multi-source engine.
    """
    async with aiohttp.ClientSession() as session:
        try:
            authors = await core.search_openalex_authors(session, name)
            if not authors:
                raise HTTPException(status_code=404, detail=f"Author '{name}' not found.")
            
            author_info = authors[0]
            author_id = author_info["id"]

            # Fetch top 10 papers to get a good sample for analysis
            raw_papers = await core.fetch_openalex_papers_by_author_id(session, author_id, max_papers=10)
            if not raw_papers:
                return {"author_info": author_info, "summary": "Author found, but no papers were available for analysis."}
            
            # Concurrently enrich all papers with full text from all sources
            enrichment_tasks = [core.enrich_paper_with_full_text(session, core.process_paper_data(p)) for p in raw_papers]
            enriched_papers = await asyncio.gather(*enrichment_tasks)

            # Generate the final summary using the fully enriched data
            summary = await core.generate_author_summary(session, author_info, enriched_papers)
            
            return {
               
                "research_summary": summary,
                "papers_analyzed": [{
                    "title": p.get('title'),
                    "year": p.get('publication_year'),
                    "citations": p.get('cited_by_count'),
                    "sources": p.get('content_sources')
                } for p in enriched_papers]
            }
        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# This matches: /paper/by-id/**
@app.get("/paper/by-id", tags=["Papers"])
async def get_paper_summary_by_id(paper_id: str = Query(..., description="OpenAlex ID or full OpenAlex URL of the paper")):
    """
    Generates a detailed, multi-source summary for a single paper by its OpenAlex ID.
    """
    search_id = paper_id.split('/')[-1] if paper_id.startswith("https://openalex.org/") else paper_id

    async with aiohttp.ClientSession() as session:
        try:
            raw_paper = await core.fetch_paper_by_id(session, search_id)
            if not raw_paper:
                raise HTTPException(status_code=404, detail=f"Paper with ID '{search_id}' not found.")

            # Run the full enrichment and summary pipeline
            paper_info = core.process_paper_data(raw_paper)
            enriched_paper = await core.enrich_paper_with_full_text(session, paper_info)
            summary = await core.generate_paper_summary(session, enriched_paper)
            
            return {"paper_info": enriched_paper, "summary": summary}
        
        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# This matches: /paper/by-title/**
@app.get("/paper/by-title", tags=["Papers"])
async def get_paper_summary_by_title(title: str = Query(..., description="Title of the paper to search for.")):
    """
    Finds a paper by its title, then generates a detailed, multi-source summary.
    """
    decoded_title = unquote(title)

    async with aiohttp.ClientSession() as session:
        try:
            # Re-using the author paper search as it's more general for titles
            params = {"filter": f"title.search:{decoded_title}", "per-page": 1, "mailto": core.MAILTO_EMAIL}
            data = await core._fetch_json(session, "https://api.openalex.org/works", params)
            
            if not data or not data.get("results"):
                raise HTTPException(status_code=404, detail=f"Paper with title '{decoded_title}' not found.")

            raw_paper = data["results"][0]
            
            # Run the full enrichment and summary pipeline
            paper_info = core.process_paper_data(raw_paper)
            enriched_paper = await core.enrich_paper_with_full_text(session, paper_info)
            summary = await core.generate_paper_summary(session, enriched_paper)
            
            return {"paper_info": enriched_paper, "summary": summary}

        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")