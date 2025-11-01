import asyncio
from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from urllib.parse import unquote
import aiohttp
from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic_settings import BaseSettings

# Local module imports
import core  # Assuming your core logic is in this module
from neo4j_repository import get_summary_from_neo4j, save_summary_to_neo4j

# --- Configuration ---
class Settings(BaseSettings):
    """Manages application settings and environment variables."""
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()

# --- Neo4j Driver Setup ---
db_driver: AsyncDriver = None

async def get_neo4j_driver() -> AsyncDriver:
    """Provides a dependency-injected Neo4j driver instance."""
    global db_driver
    if db_driver is None:
        raise RuntimeError("Database driver not initialized.")
    return db_driver

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Enhanced Author and Paper Summary Service with Neo4j Caching",
    description="Provides advanced, multi-source, LLM-generated summaries for academic authors and papers, with caching in Neo4j."
)

@app.on_event("startup")
async def startup_event():
    """Initializes the Neo4j driver on application startup."""
    global db_driver
    db_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI, 
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    # You can optionally add a connectivity check here
    await db_driver.verify_connectivity()
    print("Successfully connected to Neo4j.")


@app.on_event("shutdown")
async def shutdown_event():
    """Closes the Neo4j driver connection on application shutdown."""
    global db_driver
    if db_driver:
        await db_driver.close()
        print("Neo4j connection closed.")


# --- Updated API Endpoints ---
@app.get("/professors/summary/by-name", tags=["Professors"])
async def get_professor_summary_by_name(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Full name of the author"),
    driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """
    Generates a research summary for a professor.
    First, it checks for a cached summary in Neo4j. If not found, it generates a new one
    using a multi-source engine and saves it to the database.
    """
    # 1. Check for an existing summary in Neo4j using the repository function
    cached_summary = await get_summary_from_neo4j(driver, author_name=name)
    if cached_summary:
        return {
            "source": "cache",
            "message": "Summary retrieved from Neo4j cache.", 
            "research_summary": cached_summary
        }

    # 2. If not in cache, generate a new summary
    async with aiohttp.ClientSession() as session:
        try:
            authors = await core.search_openalex_authors(session, name)
            if not authors:
                raise HTTPException(status_code=404, detail=f"Author '{name}' not found.")
            
            author_info = authors[0]
            author_id = author_info["id"]

            raw_papers = await core.fetch_openalex_papers_by_author_id(session, author_id, max_papers=30)
            if not raw_papers:
                return {"author_info": author_info, "summary": "Author found, but no papers were available for analysis."}
            
            enrichment_tasks = [core.enrich_paper_with_full_text(session, core.process_paper_data(p)) for p in raw_papers]
            enriched_papers = await asyncio.gather(*enrichment_tasks)

            summary = await core.generate_author_summary(session, author_info, enriched_papers)

            # 3. Save the new summary to Neo4j in the background using the repository function
            background_tasks.add_task(save_summary_to_neo4j, driver, author_info, summary)
            
            return {
                "source": "generated",
                "message": "Summary generated and is being cached in Neo4j.",
                "research_summary": summary,
                "papers_analyzed_count": len(enriched_papers),
                "papers_sample": [{
                    "title": p.get('title'),
                    "year": p.get('publication_year'),
                    "citations": p.get('cited_by_count'),
                    "sources": p.get('content_sources')
                } for p in enriched_papers[:10]]
            }
        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/paper/by-id", tags=["Papers"])
async def get_paper_summary_by_id(paper_id: str = Query(..., description="OpenAlex ID or full OpenAlex URL of the paper")):
    """
    Generates a detailed, multi-source summary for a single paper by its OpenAlex ID.
    """
    print("updated endpoint called")
    search_id = paper_id.split('/')[-1] if paper_id.startswith("https://openalex.org/") else paper_id

    async with aiohttp.ClientSession() as session:
        try:
            raw_paper = await core.fetch_paper_by_id(session, search_id)
            if not raw_paper:
                raise HTTPException(status_code=404, detail=f"Paper with ID '{search_id}' not found.")

            paper_info = core.process_paper_data(raw_paper)
            enriched_paper = await core.enrich_paper_with_full_text(session, paper_info)
            summary = await core.generate_paper_summary(session, enriched_paper)
            
            # Remove full content from final response to keep it clean
            enriched_paper.pop("full_content", None)
            
            return {"paper_info": enriched_paper, "summary": summary}
        
        except aiohttp.ClientResponseError as e:
            raise HTTPException(status_code=e.status, detail=f"External API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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