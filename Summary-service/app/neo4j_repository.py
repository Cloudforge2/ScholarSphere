import json
import logging
from neo4j import AsyncDriver
from typing import Dict, Any
import time

# -------------------------
# CONFIG
# -------------------------

# Production: Cache valid for 15 days
STALE_DAYS = 15
STALE_MS = STALE_DAYS * 24 * 60 * 60 * 1000  # 15 days in milliseconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -------------------------
# STALENESS CHECK
# -------------------------

def is_stale(last_updated_ts: int | None, max_age_ms: int = STALE_MS) -> bool:
    """
    Checks if a Neo4j timestamp() value is older than the allowed age.
    Neo4j timestamp() returns milliseconds since epoch.
    """
    if not last_updated_ts:
        return True  # no timestamp = stale

    now = int(time.time() * 1000)
    age = now - last_updated_ts

    return age > max_age_ms



# -------------------------------------------------------
# AUTHOR CACHING WITH 15-DAY STALENESS CHECK
# -------------------------------------------------------

async def get_author_summary_from_neo4j(driver: AsyncDriver, author_id: str) -> Dict[str, Any] | None:
    """
    Fetches cached author summary + metadata.
    Includes staleness validation (15 days).
    """
    query = (
        "MATCH (a:Author {id: $author_id}) "
        "WHERE a.researchSummary IS NOT NULL "
        "RETURN "
        "    a.researchSummary AS summary, "
        "    a.papersAnalyzedCount AS count, "
        "    a.papersSampleJson AS sample_json, "
        "    a.lastUpdated AS last_updated"
    )

    logger.info(f"Checking Neo4j author cache for ID: {author_id}")

    async with driver.session() as session:
        result = await session.run(query, author_id=author_id)
        record = await result.single()

        if not record or not record["summary"]:
            logger.info(f"Cache miss for author ID: {author_id}")
            return None
        
        last_updated = record.get("last_updated")
        if is_stale(last_updated):
            logger.info(f"Stale author cache (or missing timestamp) for ID {author_id}. Re-ingesting.")
            return None

        logger.info(f"Fresh cache hit for author ID: {author_id}")

        papers_sample = json.loads(record["sample_json"]) if record["sample_json"] else []

        return {
            "research_summary": record["summary"],
            "papers_analyzed_count": record["count"],
            "papers_sample": papers_sample,
        }


async def save_author_summary_to_neo4j(driver: AsyncDriver, author_info: Dict[str, Any], summary_data: Dict[str, Any]):
    """
    Saves a complete author summary payload with timestamp.
    """
    author_id = author_info.get("id")
    display_name = author_info.get("display_name")

    if not author_id or not display_name:
        logger.error("Missing author ID or display name; cannot save.")
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

    logger.info(f"Saving author summary for {display_name} ({author_id})")

    try:
        async with driver.session() as session:
            await session.run(
                query,
                author_id=author_id,
                display_name=display_name,
                summary=summary_data.get("research_summary"),
                count=summary_data.get("papers_analyzed_count"),
                sample_json=papers_sample_json,
            )
        logger.info(f"Successfully saved author summary: {display_name}")
    except Exception as e:
        logger.error(f"Failed to save author summary for {display_name}: {e}")



# -------------------------------------------------------
# PAPER CACHING WITH 15-DAY STALENESS CHECK
# -------------------------------------------------------

async def get_paper_cache_from_neo4j(driver: AsyncDriver, paper_id: str) -> Dict[str, Any] | None:
    """
    Fetches cached paper info + summary + timestamp.
    Includes staleness validation (15 days).
    """
    query = (
        "MATCH (w:Work {id: $paper_id}) "
        "WHERE w.summary IS NOT NULL AND w.infoJson IS NOT NULL "
        "RETURN "
        "    w.summary AS summary, "
        "    w.infoJson AS info_json, "
        "    w.summaryLastUpdated AS last_updated"
    )

    logger.info(f"Checking Neo4j paper cache for ID: {paper_id}")

    async with driver.session() as session:
        result = await session.run(query, paper_id=paper_id)
        record = await result.single()

        if not record or not record["summary"] or not record["info_json"]:
            logger.info(f"Cache miss for paper ID: {paper_id}")
            return None

        last_updated = record.get("last_updated")
        if is_stale(last_updated):
            logger.info(f"Stale paper cache (or missing timestamp) for ID {paper_id}. Re-ingesting.")
            return None

        logger.info(f"Fresh cache hit for paper ID: {paper_id}")

        return {
            "summary": record["summary"],
            "paper_info": json.loads(record["info_json"]),
        }


async def save_paper_cache_to_neo4j(driver: AsyncDriver, paper_info: Dict[str, Any], summary: str):
    """
    Saves full paper data (info + summary) along with timestamp.
    """
    paper_id = paper_info.get("openalex_id")
    title = paper_info.get("title")

    if not paper_id or not title:
        logger.error("Paper ID or title is missing; cannot save.")
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

    logger.info(f"Saving paper cache for ID {paper_id}: {title}")

    try:
        async with driver.session() as session:
            await session.run(
                query,
                paper_id=paper_id,
                title=title,
                summary=summary,
                info_json=info_json,
            )
        logger.info(f"Successfully saved paper cache for: {title}")
    except Exception as e:
        logger.error(f"Failed to save paper cache for {title}: {e}")
