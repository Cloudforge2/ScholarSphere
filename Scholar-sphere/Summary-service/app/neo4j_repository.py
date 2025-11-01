import json
import logging
from neo4j import AsyncDriver
from typing import Dict, Any

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- AUTHOR CACHING ---

async def get_author_summary_from_neo4j(driver: AsyncDriver, author_id: str) -> Dict[str, Any] | None:
    """
    Queries Neo4j for a COMPLETE cached author response by their OpenAlex ID.
    Returns: A dictionary containing the full response payload if found, otherwise None.
    """
    query = (
        "MATCH (a:Author {id: $author_id}) "
        "WHERE a.researchSummary IS NOT NULL "
        "RETURN "
        "    a.researchSummary AS summary, "
        "    a.papersAnalyzedCount AS count, "
        "    a.papersSampleJson AS sample_json"
    )
    
    logger.info(f"Checking Neo4j author cache for ID: {author_id}")
    async with driver.session() as session:
        result = await session.run(query, author_id=author_id)
        record = await result.single()
        if record and record["summary"]:
            logger.info(f"Cache hit for author ID: {author_id}")
            papers_sample = json.loads(record["sample_json"]) if record["sample_json"] else []
            return {
                "research_summary": record["summary"],
                "papers_analyzed_count": record["count"],
                "papers_sample": papers_sample
            }
    
    logger.info(f"Cache miss for author ID: {author_id}")
    return None


async def save_author_summary_to_neo4j(driver: AsyncDriver, author_info: Dict[str, Any], summary_data: Dict[str, Any]):
    """
    Saves the COMPLETE author summary response payload to Neo4j.
    """
    author_id = author_info.get("id")
    display_name = author_info.get("display_name")
    
    if not author_id or not display_name:
        logger.error("Author ID or display name is missing. Cannot save author summary.")
        return

    papers_sample_json = json.dumps(summary_data.get("papers_sample", []))

    query = (
        "MERGE (a:Author {id: $author_id}) "
        "SET "
        "    a.displayName = $display_name, "
        "    a.researchSummary = $summary, "
        "    a.papersAnalyzedCount = $count, "
        "    a.papersSampleJson = $sample_json, "
        "    a.lastUpdated = timestamp()"
    )
    
    logger.info(f"Saving author summary for ID {author_id} to Neo4j.")
    try:
        async with driver.session() as session:
            await session.run(
                query, 
                author_id=author_id, 
                display_name=display_name, 
                summary=summary_data.get("research_summary"),
                count=summary_data.get("papers_analyzed_count"),
                sample_json=papers_sample_json
            )
        logger.info(f"Successfully saved summary for author: {display_name}")
    except Exception as e:
        logger.error(f"Failed to save author summary for {display_name}: {e}")


# --- PAPER CACHING (Corrected) ---

async def get_paper_cache_from_neo4j(driver: AsyncDriver, paper_id: str) -> Dict[str, Any] | None:
    """
    Queries Neo4j for a COMPLETE cached paper response (info and summary) by its ID.
    """
    query = (
        "MATCH (w:Work {id: $paper_id}) "
        "WHERE w.summary IS NOT NULL AND w.infoJson IS NOT NULL "
        "RETURN w.summary AS summary, w.infoJson AS info_json"
    )
    
    logger.info(f"Checking Neo4j paper cache for ID: {paper_id}")
    async with driver.session() as session:
        result = await session.run(query, paper_id=paper_id)
        record = await result.single()
        if record and record["summary"] and record["info_json"]:
            logger.info(f"Full cache hit for paper ID: {paper_id}")
            return {
                "summary": record["summary"],
                "paper_info": json.loads(record["info_json"])
            }
            
    logger.info(f"Cache miss for paper ID: {paper_id}")
    return None


async def save_paper_cache_to_neo4j(driver: AsyncDriver, paper_info: Dict[str, Any], summary: str):
    """
    Saves the COMPLETE paper response payload (info and summary) to Neo4j.
    """
    paper_id = paper_info.get("id")
    title = paper_info.get("title")

    if not paper_id or not title:
        logger.error("Paper ID or title is missing. Cannot save paper cache.")
        return

    info_json = json.dumps(paper_info)

    query = (
        "MERGE (w:Work {id: $paper_id}) "
        "ON CREATE SET w.title = $title "
        "SET "
        "    w.summary = $summary, "
        "    w.infoJson = $info_json, "
        "    w.summaryLastUpdated = timestamp()"
    )
    
    logger.info(f"Saving full paper cache for ID {paper_id} to Neo4j.")
    try:
        async with driver.session() as session:
            await session.run(query, paper_id=paper_id, title=title, summary=summary, info_json=info_json)
        logger.info(f"Successfully saved full cache for paper: {title}")
    except Exception as e:
        logger.error(f"Failed to save cache for paper {title}: {e}")