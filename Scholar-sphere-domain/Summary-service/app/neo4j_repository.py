from neo4j import AsyncDriver
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_summary_from_neo4j(driver: AsyncDriver, author_name: str) -> str | None:
    """
    Queries Neo4j for a cached research summary of an author by their display name.

    Args:
        driver: The asynchronous Neo4j driver instance.
        author_name: The full display name of the author to search for.

    Returns:
        The cached summary as a string if found, otherwise None.
    """
    query = (
        "MATCH (a:Author {displayName: $author_name}) "
        "WHERE a.researchSummary IS NOT NULL "
        "RETURN a.researchSummary AS summary"
    )
    
    logger.info(f"Checking Neo4j cache for author: {author_name}")
    async with driver.session() as session:
        result = await session.run(query, author_name=author_name)
        record = await result.single()
        if record and record["summary"]:
            logger.info(f"Cache hit for author: {author_name}")
            return record["summary"]
    
    logger.info(f"Cache miss for author: {author_name}")
    return None


async def save_summary_to_neo4j(driver: AsyncDriver, author_info: dict, summary: str):
    """
    Saves or updates an author and their research summary in Neo4j.

    This function uses MERGE to create the author node if it doesn't exist,
    or updates the summary and timestamp if it already exists.

    Args:
        driver: The asynchronous Neo4j driver instance.
        author_info: A dictionary containing author details like 'id' and 'display_name'.
        summary: The research summary string to be saved.
    """
    author_id = author_info.get("id")
    display_name = author_info.get("display_name")
    
    if not author_id or not display_name:
        logger.error("Author ID or display name is missing. Cannot save summary to Neo4j.")
        return

    query = (
        "MERGE (a:Author {id: $author_id}) "
        "ON CREATE SET "
        "    a.displayName = $display_name, "
        "    a.researchSummary = $summary, "
        "    a.lastUpdated = timestamp() "
        "ON MATCH SET "
        "    a.researchSummary = $summary, "
        "    a.lastUpdated = timestamp()"
    )
    
    logger.info(f"Saving summary for author ID {author_id} to Neo4j.")
    try:
        async with driver.session() as session:
            await session.run(
                query, 
                author_id=author_id, 
                display_name=display_name, 
                summary=summary
            )
        logger.info(f"Successfully saved summary for author: {display_name}")
    except Exception as e:
        logger.error(f"Failed to save summary for author {display_name}: {e}")