#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author Profile System with Summary & Co-authors
"""

import requests
import time
from collections import Counter
import re

# ================================================================
#                      SETUP AND HELPERS
# ================================================================

def safe_request(url, retries=3, delay=2):
    """Safe API request with retry logic"""
    for i in range(retries):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
        time.sleep(delay)
    return {}

def decode_openalex_abstract(inv_idx):
    """Decode OpenAlex inverted_index abstract"""
    if not inv_idx:
        return ""
    try:
        arr = [""] * (max(max(v) for v in inv_idx.values()) + 1)
        for word, idxs in inv_idx.items():
            for i in idxs:
                arr[i] = word
        return " ".join(arr)
    except Exception:
        return ""

# ================================================================
#                      FETCHING FROM OPENALEX
# ================================================================

def fetch_openalex_authors(name):
    """Search OpenAlex for author name"""
    url = f"https://api.openalex.org/authors?search={name}"
    data = safe_request(url)
    if not data or "results" not in data:
        return []
    return data["results"]

def fetch_openalex_papers(openalex_id, author_name):
    """Fetch author papers (sorted by citations desc)"""
    url = (
        f"https://api.openalex.org/works?"
        f"filter=authorships.author.id:https://openalex.org/{openalex_id},publication_year:>2015"
        f"&sort=cited_by_count:desc&per-page=100"
    )
    data = safe_request(url)
    if not data or "results" not in data:
        return []

    papers = []
    for w in data["results"]:
        abstract = decode_openalex_abstract(w.get("abstract_inverted_index"))

        # ✅ Safe extraction for venue
        pl = w.get("primary_location") or {}
        source = pl.get("source") if isinstance(pl, dict) else None
        venue = source.get("display_name", "Unknown") if isinstance(source, dict) else "Unknown"

        coauthors = []
        for auth in w.get("authorships", []):
            a = auth.get("author", {})
            author_display_name = a.get("display_name", "")
            
            # ✅ Filter out the main author themselves
            if author_display_name.lower() == author_name.lower():
                continue
                
            insts = auth.get("institutions")
            aff = insts[0].get("display_name", "") if insts and len(insts) > 0 else ""
            coauthors.append({
                "name": author_display_name,
                "authorId": a.get("id", ""),
                "affiliation": aff
            })

        papers.append({
            "title": w.get("title", ""),
            "venue": venue,
            "year": w.get("publication_year", "Unknown"),
            "abstract": abstract,
            "citations": w.get("cited_by_count", 0),
            "doi": w.get("doi", ""),
            "coauthors": coauthors,
            "source": "OpenAlex"
        })
    return papers

# ================================================================
#                   FETCHING FROM SEMANTIC SCHOLAR
# ================================================================

def fetch_semantic_scholar_author(name):
    """Search author in Semantic Scholar"""
    url = f"https://api.semanticscholar.org/graph/v1/author/search?query={name}&fields=name,affiliations,paperCount,url,papers&limit=5"
    data = safe_request(url)
    if not data or "data" not in data:
        return []
    return data["data"]

def fetch_semantic_scholar_papers(author_id, author_name):
    """Fetch papers from Semantic Scholar (for missing abstracts)"""
    url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers?fields=title,abstract,year,venue,citationCount,authors"
    data = safe_request(url)
    if not data or "data" not in data:
        return []

    papers = []
    for p in data["data"]:
        authors = p.get("authors", [])
        coauthors = []
        for a in authors:
            author_display_name = a.get("name", "")
            # ✅ Filter out the main author themselves
            if author_display_name.lower() == author_name.lower():
                continue
            coauthors.append({
                "name": author_display_name,
                "authorId": a.get("authorId", "")
            })

        papers.append({
            "title": p.get("title", ""),
            "venue": p.get("venue", "Unknown"),
            "year": p.get("year", "Unknown"),
            "abstract": p.get("abstract", ""),
            "citations": p.get("citationCount", 0),
            "doi": "",
            "coauthors": coauthors,
            "source": "SemanticScholar"
        })
    return papers

# ================================================================
#             RESEARCH SUMMARY GENERATION
# ================================================================

def extract_technical_terms(text):
    """Extract multi-word technical terms"""
    
    patterns = [
        r'\b(?:Cloud|Edge|Fog|IoT|Distributed|Stream|Real-time|Big Data)\s+(?:Computing|Processing|Systems|Networks|Analytics)\b',
        r'\b(?:Machine|Deep|Neural)\s+(?:Learning|Networks)\b',
        r'\b(?:Virtual|Smart|Cyber)\s+(?:Machine|City|Physical)\b',
        r'\bComplex\s+Event\s+Processing\b',
        r'\bGraph\s+Processing\b',
        r'\bFederated\s+Learning\b',
        r'\bResource\s+Scheduling\b',
        r'\bData\s+Analytics\b',
    ]
    
    terms = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        terms.extend([m.strip() for m in matches])
    
    return terms

def extract_research_themes(papers):
    """Extract main research themes from titles and abstracts"""
    all_text = " ".join([
        f"{p['title']} {p.get('abstract', '')}" 
        for p in papers if p.get('abstract')
    ])
    
    # Extract technical terms
    tech_terms = extract_technical_terms(all_text)
    
    # Count and normalize
    term_counts = Counter([t.lower() for t in tech_terms])
    
    # Get most common themes
    common_themes = [term.title() for term, _ in term_counts.most_common(10)]
    
    return common_themes

def generate_research_summary(papers, author_name):
    """Generate comprehensive rule-based research summary"""
    if not papers:
        return "No papers available to generate summary."
    
    # Filter papers with good abstracts
    good_papers = [p for p in papers if p.get('abstract') and len(p['abstract']) > 100]
    
    if len(good_papers) < 3:
        return f"{author_name}'s research focuses on distributed computing systems and cloud technologies."
    
    # Extract themes
    themes = extract_research_themes(good_papers)
    
    # Get statistics
    total_citations = sum(p['citations'] for p in papers)
    avg_citations = total_citations // len(papers) if papers else 0
    
    # Get top venues
    venue_counts = Counter([p['venue'] for p in papers if p['venue'] != 'Unknown'])
    top_venues = [v for v, _ in venue_counts.most_common(3)]
    
    # Get recent year range
    years = [p['year'] for p in papers if isinstance(p['year'], int)]
    year_range = f"{min(years)}-{max(years)}" if years else "recent years"
    
    # Identify specific contributions from top papers
    top_3 = sorted(good_papers, key=lambda x: x['citations'], reverse=True)[:3]
    contributions = []
    
    for paper in top_3:
        abstract = paper['abstract'].lower()
        title = paper['title'].lower()
        
        # Extract key contributions
        if 'propose' in abstract or 'present' in abstract:
            # Find what's being proposed
            if 'benchmark' in title or 'benchmark' in abstract:
                contributions.append("benchmark frameworks for performance evaluation")
            elif 'scheduling' in title or 'scheduling' in abstract:
                contributions.append("novel scheduling algorithms")
            elif 'architecture' in title or 'architecture' in abstract:
                contributions.append("system architectures")
            elif 'platform' in title or 'platform' in abstract:
                contributions.append("computing platforms")
    
    # Remove duplicates
    contributions = list(set(contributions))
    
    # Build summary
    summary_parts = []
    
    # Opening statement
    primary_areas = ", ".join(themes[:3]) if len(themes) >= 3 else ", ".join(themes)
    summary_parts.append(
        f"{author_name}'s research primarily focuses on {primary_areas}."
    )
    
    # Research impact
    if total_citations > 500:
        summary_parts.append(
            f"Their work has garnered significant attention with {total_citations} citations, "
            f"demonstrating substantial impact in the field."
        )
    else:
        summary_parts.append(
            f"Their research has received {total_citations} citations across {len(papers)} publications."
        )
    
    # Key contributions
    if contributions:
        contrib_str = ", ".join(contributions[:3])
        summary_parts.append(
            f"Key contributions include {contrib_str}."
        )
    
    # Research themes in detail
    if len(themes) > 3:
        additional_themes = ", ".join(themes[3:6])
        summary_parts.append(
            f"Their research also explores {additional_themes}."
        )
    
    # Publication venues
    if top_venues:
        venue_str = ", ".join(top_venues[:2])
        summary_parts.append(
            f"Their work appears in prestigious venues including {venue_str}."
        )
    
    return " ".join(summary_parts)

# ================================================================
#                          MAIN LOGIC
# ================================================================

def main():
    print("🔄 Initializing Author Profile System...\n")

    author_name = input("Enter author name: ").strip()

    # --- Fetch OpenAlex authors ---
    print("📡 Searching OpenAlex database...")
    openalex_authors = fetch_openalex_authors(author_name)
    if not openalex_authors:
        print("❌ No author found on OpenAlex.")
        return

    # --- Auto-select author with most papers ---
    oa_author = max(openalex_authors, key=lambda a: a.get("works_count", 0))
    print(f"📋 Selected author: {oa_author.get('display_name')} ({oa_author.get('works_count')} papers)")

    # --- Fetch papers ---
    print("📚 Fetching publications from OpenAlex...")
    oa_papers = fetch_openalex_papers(oa_author["id"].split("/")[-1], oa_author.get('display_name'))

    # --- If abstracts missing, fill from Semantic Scholar ---
    print("📚 Fetching additional data from Semantic Scholar...")
    ss_papers = []
    ss_authors = fetch_semantic_scholar_author(author_name)
    if ss_authors:
        ss_best = max(ss_authors, key=lambda a: a.get("paperCount", 0))
        ss_papers = fetch_semantic_scholar_papers(ss_best["authorId"], oa_author.get('display_name'))

    # Merge and deduplicate by title
    combined = {p["title"].strip().lower(): p for p in (oa_papers + ss_papers) if p["title"]}
    all_papers = list(combined.values())

    # --- Summary generation ---
    papers_with_abstracts = [p for p in all_papers if p.get('abstract') and len(p['abstract']) > 50]
    print(f"📊 Total papers merged: {len(all_papers)} | With abstracts: {len(papers_with_abstracts)}\n")
    
    print("🤖 Generating research summary...")
    summary = generate_research_summary(all_papers, oa_author.get('display_name'))
    print("✅ Summary generated successfully\n")

    # --- Display output ---
    print("=" * 80)
    print(f"AUTHOR PROFILE: {oa_author.get('display_name')}")
    print("=" * 80)
    
    # ✅ Extract affiliation with better debugging
    affiliation = "Unknown"
    last_known_inst = oa_author.get('last_known_institutions')
    
    # OpenAlex sometimes returns last_known_institutions (plural) as array
    if last_known_inst and isinstance(last_known_inst, list) and len(last_known_inst) > 0:
        affiliation = last_known_inst[0].get('display_name', 'Unknown')
    # Or last_known_institution (singular) as dict
    elif oa_author.get('last_known_institution'):
        inst = oa_author.get('last_known_institution')
        if isinstance(inst, dict):
            affiliation = inst.get('display_name', 'Unknown')
    
    print(f"Affiliation: {affiliation}")
    print(f"Total Publications: {oa_author.get('works_count', 'N/A')}")
    print(f"Citation Count: {oa_author.get('cited_by_count', 'N/A')}")
    print(f"h-index: {oa_author.get('summary_stats', {}).get('h_index', 'N/A')}\n")

    print("🧠 RESEARCH SUMMARY:")
    print(summary)
    print()

    # Extract and display research themes
    themes = extract_research_themes(papers_with_abstracts)
    if themes:
        print("🔑 KEY RESEARCH AREAS:")
        for i, theme in enumerate(themes[:8], 1):
            print(f"   {i}. {theme}")
        print()

    # Ask once whether to show abstracts
    show_abstracts = input("Show full abstracts? (y/N): ").strip().lower() == "y"

    print("\n📚 Top 20 Papers:\n")
    all_papers.sort(key=lambda p: p["citations"], reverse=True)
    for i, p in enumerate(all_papers[:20], 1):
        print("=" * 80)
        print(f"{i}. [{p['year']}] {p['title']}")
        print(f"   📊 Venue: {p['venue']} | Citations: {p['citations']} | Source: {p['source']}")
        if p["coauthors"]:
            print(f"   👥 Co-authors ({len(p['coauthors'])}):")
            for ca in p["coauthors"][:25]:
                aff = ca.get('affiliation', '')
                aid = ca.get('authorId', '')
                print(f"      • {ca['name']} | {aff} | ID:{aid}")
        if show_abstracts and p.get("abstract"):
            print(f"   📄 Abstract: {p['abstract']}\n")

# ================================================================
#                           ENTRY POINT
# ================================================================

if __name__ == "__main__":
    main()
