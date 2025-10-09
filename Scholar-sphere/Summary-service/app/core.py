#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Author Profile System with llama based model Summaries
Features:
- Fetches author info and top papers from OpenAlex
- Fetches abstracts from Semantic Scholar in parallel
- Generates detailed author summaries using LLama3.1 model 
- Falls back to rule-based summary if LLM fails
- Shows author metrics and affiliations
"""

import requests
import asyncio
import aiohttp
import re
import ollama
from typing import List
from collections import Counter

# -----------------------------
# LLM Configuration
# -----------------------------
LLM_MODEL = "llama3.1:8b"

# -----------------------------
# OpenAlex Author & Paper Fetching
# -----------------------------
def fetch_author_candidates(author_name: str, max_results: int = 10):
    """Fetch multiple author candidates from OpenAlex."""
    url = f"https://api.openalex.org/authors?search={author_name}&per-page={max_results}"
    r = requests.get(url)
    r.raise_for_status()
    authors = r.json().get("results", [])
    return authors

def display_author_candidates(authors: List[dict]) -> dict:
    """Display author candidates and let user select one."""
    print("\n" + "=" * 80)
    print("🔍 FOUND MULTIPLE AUTHORS - Please select one:")
    print("=" * 80)
    
    for i, author in enumerate(authors, 1):
        display_name = author.get("display_name", "Unknown")
        
        # Get affiliation
        affiliation = "N/A"
        last_institution = author.get("last_known_institution", {})
        if last_institution:
            affiliation = last_institution.get("display_name", "N/A")
        
        # If still N/A, try last_known_institutions array
        if affiliation == "N/A":
            institutions = author.get("last_known_institutions", [])
            if institutions:
                affiliation = institutions[0].get("display_name", "N/A")
        
        works_count = author.get("works_count", 0)
        cited_by_count = author.get("cited_by_count", 0)
        h_index = author.get("summary_stats", {}).get("h_index", 0)
        
        print(f"\n{i}. {display_name}")
        print(f"   📍 Affiliation: {affiliation}")
        print(f"   📊 Papers: {works_count} | 📈 Citations: {cited_by_count} | 🎯 h-index: {h_index}")
    
    print("\n" + "=" * 80)
    
    # Get user selection
    while True:
        try:
            choice = input(f"\nSelect author (1-{len(authors)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(authors):
                return authors[choice_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(authors)}")
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q' to quit")

def fetch_openalex_papers(author_id: str, max_papers: int = 20):
    """Fetch papers for a specific author ID."""
    url = f"https://api.openalex.org/works?filter=authorships.author.id:{author_id}&sort=cited_by_count:desc&per-page={max_papers}"
    r = requests.get(url)
    r.raise_for_status()
    papers_data = r.json().get("results", [])
    
    papers = []
    for item in papers_data:
        # Decode inverted abstract index if present
        abstract = ""
        inv_abstract = item.get("abstract_inverted_index")
        if inv_abstract:
            try:
                max_pos = max([max(positions) for positions in inv_abstract.values()])
                words = [""] * (max_pos + 1)
                for word, positions in inv_abstract.items():
                    for pos in positions:
                        words[pos] = word
                abstract = " ".join(words)
            except:
                abstract = ""
        
        # Get venue information
        primary_location = item.get("primary_location", {})
        venue = ""
        if primary_location:
            source = primary_location.get("source", {})
            if source:
                venue = source.get("display_name", "")
        
        # Fallback to host_venue if primary_location doesn't have venue
        if not venue:
            venue = item.get("host_venue", {}).get("display_name", "")
        
        # Get title, handle None case
        title = item.get("display_name") or item.get("title", "Untitled")
        
        papers.append({
            "title": title,
            "year": item.get("publication_year", "N/A"),
            "venue": venue if venue else "N/A",
            "cited_by_count": item.get("cited_by_count", 0),
            "abstract": abstract,
            "openalex_id": item.get("id", "")
        })
    
    return papers

# -----------------------------
# Semantic Scholar Abstract Fetching
# -----------------------------
async def fetch_semantic_abstract(session, title: str) -> str:
    """Fetch abstract from Semantic Scholar."""
    try:
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": title, "limit": 1, "fields": "title,abstract"}
        async with session.get(search_url, params=params) as resp:
            if resp.status != 200:
                return ""
            data = await resp.json()
            papers = data.get("data", [])
            if papers and papers[0].get("abstract"):
                return papers[0]["abstract"]
    except Exception:
        pass
    return ""

async def enrich_papers_with_abstracts(papers: List[dict]) -> List[dict]:
    """Enrich papers with Semantic Scholar abstracts in parallel."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_semantic_abstract(session, p["title"]) for p in papers]
        results = await asyncio.gather(*tasks)
        
        for paper, ss_abstract in zip(papers, results):
            if ss_abstract:
                # Combine OpenAlex + Semantic Scholar abstracts
                if paper["abstract"]:
                    paper["combined_abstract"] = paper["abstract"] + " " + ss_abstract
                else:
                    paper["combined_abstract"] = ss_abstract
            else:
                paper["combined_abstract"] = paper["abstract"]
    
    return papers

# -----------------------------
# Rule-based summary fallback
# -----------------------------
def rule_based_summary(author_name: str, papers: List[dict]) -> str:
    """Generate rule-based summary from paper abstracts."""
    all_text = " ".join([p.get("combined_abstract", "") for p in papers])
    words = re.findall(r"\b[a-zA-Z]{5,}\b", all_text.lower())
    counter = Counter(words)
    
    # Filter out common words
    stopwords = {"based", "using", "paper", "approach", "method", "system", "systems", 
                 "research", "study", "results", "proposed", "present", "provide"}
    keywords = [w for w, _ in counter.most_common(20) if w not in stopwords][:10]
    
    summary = f"{author_name} has published {len(papers)} highly-cited papers. "
    summary += f"Main research areas include: {', '.join(keywords)}. "
    
    total_citations = sum(p.get("cited_by_count", 0) for p in papers)
    summary += f"These papers have received {total_citations} citations in total."
    
    return summary

# -----------------------------
# LLM Summary Generation
# -----------------------------
def generate_author_summary(author_name: str, author_info: dict, papers: List[dict]) -> str:
    """Generate author summary using LLM with fallback."""
    # Prepare context with paper titles and abstracts
    papers_text = []
    for i, p in enumerate(papers[:15], 1):  # Limit to top 15 to avoid token limits
        abstract = p.get("combined_abstract", "")[:500]  # Truncate long abstracts
        papers_text.append(f"{i}. {p['title']} ({p.get('year', 'N/A')})\n   Abstract: {abstract}")
    
    combined_text = "\n\n".join(papers_text)
    
    # Build comprehensive prompt
    affiliation = author_info.get("last_known_institution", {})
    if affiliation:
        affiliation_name = affiliation.get("display_name", "Unknown")
    else:
        affiliation_name = "Unknown"
    
    # Also try to get affiliation from last_known_institutions array
    if affiliation_name == "Unknown":
        institutions = author_info.get("last_known_institutions", [])
        if institutions:
            affiliation_name = institutions[0].get("display_name", "Unknown")
    
    total_works = author_info.get("works_count", 0)
    total_citations = author_info.get("cited_by_count", 0)
    h_index = author_info.get("summary_stats", {}).get("h_index", 0)
    
    prompt = f"""You are analyzing the research profile of {author_name}, a researcher affiliated with {affiliation_name}.

Author Metrics:
- Total Publications: {total_works}
- Total Citations: {total_citations}
- h-index: {h_index}

Based on the following top papers and their abstracts, write a comprehensive research summary (2-3 paragraphs) covering:
1. Main research areas and themes
2. Key methodologies and approaches
3. Notable contributions and impact

Top Papers:
{combined_text}

Write a detailed, coherent summary of {author_name}'s research profile:"""

    try:
        response = ollama.generate(model=LLM_MODEL, prompt=prompt)
        summary = response.get("response", "")
        
        if not summary.strip():
            raise ValueError("Empty summary from LLM")
        
        return summary.strip()
    
    except Exception as e:
        print(f"⚠️  LLM failed: {e}")
        print("📝 Using rule-based summary instead...\n")
        return rule_based_summary(author_name, papers)

# -----------------------------
# Main Function
# -----------------------------
def main():
    print("🔍 Enhanced Author Profile System\n")
    author_name = input("Enter author name: ").strip()
    
    # Step 1: Fetch author candidates
    print(f"\n📋 Searching for: {author_name}")
    authors = fetch_author_candidates(author_name)
    
    if not authors:
        print("❌ No authors found in OpenAlex")
        return
    
    # Step 2: Let user select the correct author
    if len(authors) == 1:
        print(f"✅ Found: {authors[0].get('display_name', author_name)}")
        author_info = authors[0]
    else:
        author_info = display_author_candidates(authors)
        if not author_info:
            print("\n👋 Exiting...")
            return
        print(f"\n✅ Selected: {author_info.get('display_name', author_name)}")
    
    author_id = author_info["id"]
    display_name = author_info.get("display_name", author_name)
    
    # Step 3: Fetch papers
    print(f"\n📚 Fetching top papers from OpenAlex...")
    papers = fetch_openalex_papers(author_id)
    
    if not papers:
        print("❌ No papers found for this author")
        return
    
    # Step 4: Enrich with Semantic Scholar abstracts
    print("🔄 Enriching with Semantic Scholar abstracts...")
    papers = asyncio.run(enrich_papers_with_abstracts(papers))
    
    # Step 5: Generate LLM summary
    print(f"🤖 Generating research summary using {LLM_MODEL}...\n")
    summary = generate_author_summary(display_name, author_info, papers)
    
    # -----------------------------
    # Display Results
    # -----------------------------
    print("=" * 80)
    print(f"AUTHOR PROFILE: {display_name}")
    print("=" * 80)
    
    # Get affiliation with better handling
    affiliation = author_info.get("last_known_institution", {})
    if affiliation:
        affiliation_name = affiliation.get("display_name", "N/A")
    else:
        affiliation_name = "N/A"
    
    # Try alternate affiliation field
    if affiliation_name == "N/A":
        institutions = author_info.get("last_known_institutions", [])
        if institutions:
            affiliation_name = institutions[0].get("display_name", "N/A")
    
    # Get affiliation from affiliations array if still not found
    if affiliation_name == "N/A":
        affiliations = author_info.get("affiliations", [])
        if affiliations:
            affiliation_name = affiliations[0].get("institution", {}).get("display_name", "N/A")
    
    print(f"📍 Affiliation: {affiliation_name}")
    print(f"📊 Total Publications: {author_info.get('works_count', 0)}")
    print(f"📈 Total Citations: {author_info.get('cited_by_count', 0)}")
    print(f"🎯 h-index: {author_info.get('summary_stats', {}).get('h_index', 0)}")
    
    print("\n" + "=" * 80)
    print("🧠 RESEARCH SUMMARY")
    print("=" * 80)
    print(summary)
    
    print("\n" + "=" * 80)
    print("📚 TOP PAPERS")
    print("=" * 80)
    
    # Ask if user wants to see abstracts
    show_abstracts = input("\n📄 Show paper abstracts? (y/N): ").strip().lower() == 'y'
    print()
    
    for i, p in enumerate(papers, start=1):
        print(f"\n{i}. {p['title']}")
        print(f"   📅 Year: {p.get('year', 'N/A')} | 📊 Citations: {p.get('cited_by_count', 0)}")
        print(f"   🏛️  Venue: {p.get('venue', 'N/A')}")
        
        if show_abstracts:
            abstract = p.get('combined_abstract', '') or p.get('abstract', '')
            if abstract:
                # Truncate very long abstracts for readability
                if len(abstract) > 500:
                    abstract = abstract[:500] + "..."
                print(f"   📝 Abstract: {abstract}")
            else:
                print(f"   📝 Abstract: Not available")

if __name__ == "__main__":
    main()
