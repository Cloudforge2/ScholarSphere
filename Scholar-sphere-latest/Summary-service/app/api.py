#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI application for the Enhanced Author and Paper Summary Service.

This script provides API endpoints to generate or retrieve research summaries
for authors and papers, utilizing the functionalities from kc_core.py.
It integrates with a Neo4j database for caching to improve performance.

Key Design Points:
- Uses FastAPI for modern, high-performance web APIs.
- Interacts with a Neo4j database for persistent caching of results.
- Wraps synchronous functions from `kc_core.py` (which use `requests`)
  in `asyncio.to_thread` to prevent blocking the server's event loop.
- Uses `aiohttp` only where absolutely necessary for async operations if any.
- Provides background tasks for caching to return responses to the user faster.
"""

import asyncio
import logging
import requests
from urllib.parse import unquote
import os
from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic_settings import BaseSettings

# Import the core logic from your kc_core script
import kc_core as core

# NOTE: You need to have a `neo4j_repository.py` file with the specified functions.
# This is a placeholder for the actual import.
from neo4j_repository import (
    get_author_summary_from_neo4j,
    save_author_summary_to_neo4j,
    get_paper_cache_from_neo4j,
    save_paper_cache_to_neo4j
)

# --- Configuration & Boilerplate ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Loads configuration from environment variables or a .env file."""
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    GROQ_API_KEY: str
    class Config:
        env_file = ".env"

settings = Settings()
db_driver: AsyncDriver = None

async def get_neo4j_driver() -> AsyncDriver:
    """Dependency function to get the Neo4j driver instance."""
    global db_driver
    if db_driver is None:
        raise RuntimeError("Database driver not initialized.")
    return db_driver

app = FastAPI(
    title="Enhanced Author and Paper Summary Service",
    description="Provides advanced, multi-source summaries for authors and papers with Neo4j caching, powered by kc_core."
)

@app.on_event("startup")
async def startup_event():
    """Initializes the Neo4j database driver on application startup."""
    
    # --- START: DEBUGGING BLOCK ---
    
    # First, let's see if the settings object loaded the key from the .env file
    print("--- [DEBUGGING API KEY] ---")
    groq_key_from_settings = settings.GROQ_API_KEY

    if groq_key_from_settings:
        print("✅ Pydantic settings successfully loaded GROQ_API_KEY.")
        
        # !! WARNING: Only print the full key for local debugging.
        # !! NEVER do this in a production environment.
        # print(f"   INSECURE - Full Key: {groq_key_from_settings}")

        # RECOMMENDED: Print a masked version for verification.
        masked_key = f"{groq_key_from_settings[:4]}...{groq_key_from_settings[-4:]}"
        print(f"   SAFE - Masked Key: {masked_key}")

        # Now, set it as an environment variable for kc_core.py to use
        os.environ["GROQ_API_KEY"] = groq_key_from_settings
        print("   Key has been set as an environment variable.")

    else:
        print("❌ ERROR: GROQ_API_KEY was NOT found in the .env file or environment.")
        print("   The application will likely fail to make LLM calls.")

    print("--- [END DEBUGGING] ---")
    
    # --- END: DEBUGGING BLOCK ---


    # Your existing database connection logic
    global db_driver
    db_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    await db_driver.verify_connectivity()
    print("Successfully connected to Neo4j.")

@app.on_event("shutdown")
async def shutdown_event():
    """Closes the Neo4j database driver on application shutdown."""
    global db_driver
    if db_driver:
        await db_driver.close()

# --- API ENDPOINTS ---
# In your FastAPI script (main.api.py)

@app.get("/professors/summary/by-id", tags=["Professors"])
async def get_professor_summary_by_id(
    background_tasks: BackgroundTasks,
    id: str = Query(..., description="OpenAlex ID of the author (e.g., A5023888391)"),
    driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """
    Generates or retrieves a research summary for a professor by their OpenAlex ID.
    Caches the results in Neo4j for fast subsequent lookups.
    """
    cached_data = await get_author_summary_from_neo4j(driver, author_id=id)
    if cached_data:
        return {
            "source": "cache",
            "message": "Summary and data retrieved from Neo4j cache.",
            **cached_data
        }

    try:
        author_info = await asyncio.to_thread(core.fetch_author_by_id, id)
        if not author_info:
            raise HTTPException(status_code=404, detail=f"Author with ID '{id}' not found in OpenAlex.")

        raw_papers = await asyncio.to_thread(core.fetch_all_openalex_papers, author_info['id'], max_papers=20)
        if not raw_papers:
            return {"author_info": author_info, "summary": "Author found, but no papers were available for analysis."}

        enriched_papers = await core.enrich_papers_with_content(raw_papers)

        # ------------------------------------------------------------------- #
        # --- KEY CHANGE: THE INEFFICIENT LOOP FOR PAPER SUMMARIES IS GONE ---
        #
        # We no longer call generate_paper_summary for every paper here.
        # We only need the paper content, which is already in enriched_papers.
        # We will also stop caching individual papers from this endpoint to
        # keep its purpose focused on the author.
        #
        # ------------------------------------------------------------------- #
        
        # Generate the main author summary in a thread (This makes ONE API call)
        author_summary = await asyncio.to_thread(
            core.generate_author_summary,
            author_info['display_name'],
            author_info,
            enriched_papers
        )

        response_data = {
            "research_summary": author_summary,
            "papers_analyzed_count": len(enriched_papers),
            "papers_sample": [{
                "title": p.get('title'), "year": p.get('year'),
                "citations": p.get('cited_by_count'), "sources": p.get('content_source')
            } for p in enriched_papers[:10]]
        }

        # Cache the complete author response object
        background_tasks.add_task(save_author_summary_to_neo4j, driver, author_info, response_data)

        return {
            "source": "generated",
            "message": "Summary generated and is being cached in Neo4j.",
            **response_data
        }
    except requests.exceptions.HTTPError as e:
        # Handle cases where Groq rate limits the single author summary call
        if e.response.status_code == 429:
             logger.warning("Groq API rate limit hit while generating author summary. Falling back.")
             # You can decide what to return here. Maybe a rule-based summary or a specific message.
             return {"author_info": author_info, "summary": "Could not generate summary due to API limits. Please try again later."}
        raise HTTPException(status_code=500, detail=f"An HTTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Error in get_professor_summary_by_id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    


@app.get("/paper/by-id", tags=["Papers"])
async def get_paper_summary_by_id(
    background_tasks: BackgroundTasks,
    paper_id: str = Query(..., description="OpenAlex ID (e.g., W2755952924)"),
    driver: AsyncDriver = Depends(get_neo4j_driver)
):
    """
    Generates or retrieves a summary for a single paper by its OpenAlex ID.
    Follows a 'cache-first' strategy.
    """
    search_id_full = f"https://openalex.org/{paper_id.split('/')[-1]}"
    if not paper_id.startswith("https://openalex.org/"):
        search_id_full = f"https://openalex.org/{paper_id.split('/')[-1]}"
    else:
        search_id_full = paper_id
    cached_response = await get_paper_cache_from_neo4j(driver, paper_id=search_id_full)
    if cached_response:
        return {"source": "cache", **cached_response}

    try:
        # kc_core.py does not have a fetch_paper_by_id, so we do it here
        # using `requests` in a thread for consistency.
        

        raw_paper_data = await asyncio.to_thread(core.fetch_paper_by_id, search_id_full)
        if not raw_paper_data:
             raise HTTPException(status_code=404, detail=f"Paper with ID '{search_id_full}' not found.")

        # Manually map the raw paper data into the structure expected by enrichment
        paper_info = {
            "title": raw_paper_data.get("display_name"), "year": raw_paper_data.get("publication_year"),
            "venue": raw_paper_data.get("host_venue", {}).get("display_name", "N/A"),
            "cited_by_count": raw_paper_data.get("cited_by_count", 0),
            "abstract": core.sanitize_text(str(raw_paper_data.get("abstract_inverted_index"))), # Simplified
            "coauthors": core.extract_coauthors(raw_paper_data.get("authorships", []), ""),
            "arxiv_id": raw_paper_data.get("ids", {}).get("arxiv"), "doi": raw_paper_data.get("doi"),
            "openalex_id": raw_paper_data.get("id")
        }

        enriched_papers = await core.enrich_papers_with_content([paper_info])
        if not enriched_papers:
            raise HTTPException(status_code=500, detail="Failed to enrich paper content.")
        enriched_paper = enriched_papers[0]

        summary = core.generate_paper_summary(enriched_paper)
        paper_to_cache = enriched_paper.copy()
        paper_to_cache.pop("full_content", None)

        background_tasks.add_task(save_paper_cache_to_neo4j, driver, paper_to_cache, summary)

        return {"source": "generated", "paper_info": paper_to_cache, "summary": summary}

    except Exception as e:
        logger.error(f"Error in get_paper_summary_by_id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/paper/by-title", tags=["Papers"])
async def get_paper_summary_by_title(
    title: str = Query(..., description="Title of the paper to search for.")
):
    """
    Finds a paper by its title, then generates a detailed, multi-source summary.
    This endpoint does not use caching.
    """
    decoded_title = unquote(title)

    try:
        # Use kc_core's synchronous fetch_author_candidates, but for works
        def search_paper_sync(search_title):
            url = f"https://api.openalex.org/works?search={search_title}&per-page=1"
            r = requests.get(url)
            r.raise_for_status()
            return r.json()

        data = await asyncio.to_thread(search_paper_sync, decoded_title)
        if not data or not data.get("results"):
            raise HTTPException(status_code=404, detail=f"Paper with title '{decoded_title}' not found.")
        raw_paper = data["results"][0]

        # Map the data
        paper_info = {
            "title": raw_paper.get("display_name"), "year": raw_paper.get("publication_year"),
            "venue": raw_paper.get("host_venue", {}).get("display_name", "N/A"),
            "cited_by_count": raw_paper.get("cited_by_count", 0),
            "abstract": core.sanitize_text(str(raw_paper.get("abstract_inverted_index"))), # Simplified
            "coauthors": core.extract_coauthors(raw_paper.get("authorships", []), ""),
            "arxiv_id": raw_paper.get("ids", {}).get("arxiv"), "doi": raw_paper.get("doi"),
            "openalex_id": raw_paper.get("id")
        }

        enriched_papers = await core.enrich_papers_with_content([paper_info])
        if not enriched_papers:
             raise HTTPException(status_code=500, detail="Failed to enrich paper content.")
        enriched_paper = enriched_papers[0]

        summary = core.generate_paper_summary(enriched_paper)
        enriched_paper.pop("full_content", None)

        return {"paper_info": enriched_paper, "summary": summary}

    except Exception as e:
        logger.error(f"Error in get_paper_summary_by_title: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")