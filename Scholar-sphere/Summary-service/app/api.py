import asyncio
import logging
from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from urllib.parse import unquote
import aiohttp
from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic_settings import BaseSettings

# Local module imports
import core
from neo4j_repository import (
    get_author_summary_from_neo4j,
    save_author_summary_to_neo4j,
    get_paper_cache_from_neo4j,  # Correct function for full paper cache
    save_paper_cache_to_neo4j   # Correct function for full paper cache
)

# --- Configuration & Boilerplate ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    class Config: env_file = ".env"

settings = Settings()
db_driver: AsyncDriver = None

async def get_neo4j_driver() -> AsyncDriver:
    global db_driver
    if db_driver is None: raise RuntimeError("Database driver not initialized.")
    return db_driver

app = FastAPI(
    title="Enhanced Author and Paper Summary Service",
    description="Provides advanced, multi-source summaries for authors and papers with Neo4j caching."
)

@app.on_event("startup")
async def startup_event():
    global db_driver
    db_driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD))
    await db_driver.verify_connectivity()
    print("Successfully connected to Neo4j.")

@app.on_event("shutdown")
async def shutdown_event():
    global db_driver
    if db_driver: await db_driver.close()


# --- API ENDPOINTS ---

@app.get("/professors/summary/by-id", tags=["Professors"])
async def get_professor_summary_by_id(
    background_tasks: BackgroundTasks,
    id: str = Query(..., description="OpenAlex ID of the author (e.g., A5023888391)"),
    driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """
    Generates or retrieves a research summary for a professor by their OpenAlex ID.
    While generating, it also individually caches the summaries of the papers analyzed.
    """
    cached_data = await get_author_summary_from_neo4j(driver, author_id=id)
    if cached_data:
        return {
            "source": "cache",
            "message": "Summary and data retrieved from Neo4j cache.",
            **cached_data
        }

    async with aiohttp.ClientSession() as session:
        try:
            author_info = await core.fetch_author_by_id(session, id)
            if not author_info:
                raise HTTPException(status_code=404, detail=f"Author with ID '{id}' not found.")
            
            raw_papers = await core.fetch_openalex_papers_by_author_id(session, id, max_papers=30)
            if not raw_papers:
                return {"author_info": author_info, "summary": "Author found, but no papers were available for analysis."}
            
            enrichment_tasks = [core.enrich_paper_with_full_text(session, core.process_paper_data(p)) for p in raw_papers]
            enriched_papers = await asyncio.gather(*enrichment_tasks)

            # Generate and cache individual paper summaries in the background
            paper_summary_tasks = [core.generate_paper_summary(session, p) for p in enriched_papers]
            individual_summaries = await asyncio.gather(*paper_summary_tasks)
            
            for paper, summary in zip(enriched_papers, individual_summaries):
                if summary and "Not enough content" not in summary:
                    background_tasks.add_task(save_paper_summary_to_neo4j, driver, paper, summary)
            
            # Generate the main author summary
            author_summary = await core.generate_author_summary(session, author_info, enriched_papers)
            
            response_data = {
                "research_summary": author_summary,
                "papers_analyzed_count": len(enriched_papers),
                "papers_sample": [{
                    "title": p.get('title'), "year": p.get('publication_year'),
                    "citations": p.get('cited_by_count'), "sources": p.get('content_sources')
                } for p in enriched_papers[:10]]
            }

            # Cache the complete author response object
            background_tasks.add_task(save_author_summary_to_neo4j, driver, author_info, response_data)
            
            return {
                "source": "generated",
                "message": "Summary generated and is being cached in Neo4j.",
                **response_data
            }
        except Exception as e:
            logger.error(f"Error in get_professor_summary_by_id: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/paper/by-id", tags=["Papers"])
async def get_paper_summary_by_id(
    background_tasks: BackgroundTasks,
    paper_id: str = Query(..., description="OpenAlex ID (e.g., W2755952924 or full URL)"),
    driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """
    Generates or retrieves a fully cached summary and info for a single paper by its ID.
    This endpoint follows a 'cache-first' strategy for maximum performance.
    """
    # 1. Standardize the incoming ID to the full URL format for consistency.
    if not paper_id.startswith("https://openalex.org/"):
        search_id_full = f"https://openalex.org/{paper_id.split('/')[-1]}"
    else:
        search_id_full = paper_id

    # 2. Check the cache FIRST, before doing anything else.
    cached_response = await get_paper_cache_from_neo4j(driver, paper_id=search_id_full)
    if cached_response:
        # If we have a hit, return immediately. This is the fast path.
        return {
            "source": "cache",
            **cached_response  # Unpacks to {"paper_info": ..., "summary": ...}
        }

    # 3. If (and only if) there is a cache miss, proceed with the full generation logic.
    async with aiohttp.ClientSession() as session:
        try:
            raw_paper = await core.fetch_paper_by_id(session, search_id_full)
            if not raw_paper:
                raise HTTPException(status_code=444, detail=f"Paper with ID '{search_id_full}' not found in OpenAlex.")
            
            paper_info = core.process_paper_data(raw_paper)
            
            # Enrich the paper data with full text from multiple sources.
            enriched_paper = await core.enrich_paper_with_full_text(session, paper_info)
            # Generate the summary using the enriched data.
            summary = await core.generate_paper_summary(session, enriched_paper)
            
            # Important: Remove large, unnecessary data before caching the response payload.
            enriched_paper.pop("full_content", None)
            
            # 4. Save the complete payload (paper_info + summary) to the cache in the background.
            background_tasks.add_task(save_paper_cache_to_neo4j, driver, enriched_paper, summary)
            
            # 5. Return the newly generated data.
            return {"source": "generated", "paper_info": enriched_paper, "summary": summary}
        
        except Exception as e:
            logger.error(f"Error in get_paper_summary_by_id: {e}", exc_info=True)
            raise HTTPException(status_code=555, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/paper/by-title", tags=["Papers"])
async def get_paper_summary_by_title(title: str = Query(..., description="Title of the paper to search for.")):
    """
    Finds a paper by its title, then generates a detailed, multi-source summary.
    """
    print("updated by-title endpoint called")
    decoded_title = unquote(title)

    async with aiohttp.ClientSession() as session:
        try:
            params = {"filter": f"title.search:{decoded_title}", "per-page": 1, "mailto": core.MAILTO_EMAIL}
            data = await core._fetch_json(session, "https://api.openalex.org/works", params)
            
            if not data or not data.get("results"):
                raise HTTPException(status_code=404, detail=f"Paper with title '{decoded_title}' not found.")

            raw_paper = data["results"][0]
            
            paper_info = core.process_paper_data(raw_paper)
            enriched_paper = await core.enrich_paper_with_full_text(session, paper_info)
            summary = await core.generate_paper_summary(session, enriched_paper)
            
            # Remove full content from final response
            enriched_paper.pop("full_content", None)

            return {"paper_info": enriched_paper, "summary": summary}

        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")