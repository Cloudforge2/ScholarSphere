#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Author Profile System with Multiple Data Sources and Deduplication
Features:
- Fetches from OpenAlex, arXiv, Semantic Scholar, Unpaywall, Crossref
- Removes duplicate content from multiple sources
- Downloads and parses PDFs from multiple sources
- Shows co-authors and their affiliations
- Generates detailed summaries using advanced LLM (LLama 3.3:70B Model)
"""

import requests
import asyncio
import aiohttp
import re
# Use GroqCloud (OpenAI-compatible) for LLM calls if GROQ_API_KEY is provided.
# The script will fall back to rule-based summary if the Groq call fails or key is missing.
from typing import List, Dict, Optional, Set
from collections import Counter
import xml.etree.ElementTree as ET
import os
from pathlib import Path
import tempfile
import base64
import io
from urllib.parse import quote
import time
import json
import hashlib

# -----------------------------
# LLM Configuration
# -----------------------------
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.3:70b")
# Groq settings (use GROQ_API_KEY env var). Default Groq model id:
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", None)

# Local cache for domain classifications to avoid repeated LLM calls
DOMAIN_CACHE_FILE = os.path.join(os.path.dirname(__file__), "domain_cache.json")


def load_domain_cache() -> Dict:
    try:
        if os.path.exists(DOMAIN_CACHE_FILE):
            with open(DOMAIN_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_domain_cache(cache: Dict):
    try:
        with open(DOMAIN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def generate_with_groq(prompt: str, model: str = None, max_tokens: int = 1024, temperature: float = 0.2, max_retries: int = 3) -> str:
    """Call GroqCloud's OpenAI-compatible Chat Completions endpoint with retry logic.

    Returns the generated text, or raises an exception on HTTP/errors.
    """
    api_key = GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")

    model = model or GROQ_MODEL
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Retry with exponential backoff for rate limiting
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                    print(f"   ⏳ Rate limited. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
            raise
        except Exception:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                print(f"   ⏳ Request failed. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise

    # Try common OpenAI-compatible fields
    try:
        choices = data.get("choices") or []
        if choices:
            first = choices[0]
            # chat/completions: message.content
            if isinstance(first, dict):
                msg = first.get("message", {}) if first.get("message") else first
                if isinstance(msg, dict):
                    content = msg.get("content") or msg.get("text")
                    if content:
                        return content
            # fallback: text
            text = first.get("text")
            if text:
                return text
    except Exception:
        pass

    # other possible field
    if isinstance(data.get("output_text"), str):
        return data.get("output_text")

    # last resort: stringify entire response
    return json.dumps(data)

# -----------------------------
# PDF Processing (Pure Python)
# -----------------------------
def extract_text_from_pdf(pdf_data: bytes) -> Optional[str]:
    """Extract text from PDF using pure Python libraries."""
    try:
        # Try using PyPDF2 first
        try:
            import PyPDF2
            pdf_stream = io.BytesIO(pdf_data)
            reader = PyPDF2.PdfReader(pdf_stream)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            if text.strip():
                return text
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  PyPDF2 extraction failed: {e}")
        
        # Try using pdfplumber
        try:
            import pdfplumber
            pdf_stream = io.BytesIO(pdf_data)
            with pdfplumber.open(pdf_stream) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                if text.strip():
                    return text
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  pdfplumber extraction failed: {e}")
        
        return None
    except Exception as e:
        print(f"⚠️  Error extracting PDF text: {e}")
        return None

# -----------------------------
# Text Processing and Deduplication
# -----------------------------
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Remove extra whitespace, convert to lowercase
    text = re.sub(r'\s+', ' ', text.strip())
    return text.lower()

def get_text_hash(text: str) -> str:
    """Get hash of normalized text for comparison."""
    normalized = normalize_text(text)
    return hashlib.md5(normalized.encode()).hexdigest()

def is_duplicate(text1: str, text2: str, threshold: float = 0.9) -> bool:
    """Check if two texts are duplicates using similarity threshold."""
    if not text1 or not text2:
        return False
    
    # Quick hash check first
    if get_text_hash(text1) == get_text_hash(text2):
        return True
    
    # For short texts, check exact match after normalization
    if len(text1) < 200 and len(text2) < 200:
        return normalize_text(text1) == normalize_text(text2)
    
    # For longer texts, check if one is contained in the other
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Check similarity ratio for longer texts
    if len(norm1) > 100 and len(norm2) > 100:
        # Simple similarity check
        common_words = set(norm1.split()) & set(norm2.split())
        total_words = set(norm1.split()) | set(norm2.split())
        if total_words:
            similarity = len(common_words) / len(total_words)
            return similarity > threshold
    
    return False

def deduplicate_content(content_list: List[tuple]) -> List[tuple]:
    """Remove duplicate content from a list of (content, source) tuples."""
    if not content_list:
        return []
    
    unique_content = []
    seen_hashes: Set[str] = []
    
    for content, source in content_list:
        if not content or not content.strip():
            continue
        
        content_hash = get_text_hash(content)
        
        # Check if this content is a duplicate of anything we've seen
        is_dup = False
        for seen_hash in seen_hashes:
            if content_hash == seen_hash:
                is_dup = True
                break
        
        # Also check against existing unique content for near-duplicates
        if not is_dup:
            for existing_content, _ in unique_content:
                if is_duplicate(content, existing_content):
                    is_dup = True
                    break
        
        if not is_dup:
            unique_content.append((content, source))
            seen_hashes.append(content_hash)
    
    return unique_content

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


def fetch_author_by_orcid(orcid: str) -> Optional[dict]:
    """Fetch an OpenAlex author by ORCID identifier."""
    if not orcid:
        return None
    try:
        # Clean ORCID (remove https://orcid.org/ if present)
        orcid = orcid.strip().replace("https://orcid.org/", "")
        url = f"https://api.openalex.org/authors?filter=orcid:{orcid}"
        r = requests.get(url)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            return results[0]
    except Exception as e:
        print(f"⚠️  ORCID lookup failed: {e}")
    return None

def display_author_candidates(authors: List[dict]) -> dict:
    """Display author candidates and let user select one."""
    print("\n" + "=" * 80)
    print("🔍 FOUND MULTIPLE AUTHORS - Please select one:")
    print("=" * 80)
    
    for i, author in enumerate(authors, 1):
        display_name = author.get("display_name", "Unknown")
        
        # Get ORCID
        orcid = author.get("orcid", "N/A")
        if orcid and orcid.startswith("https://orcid.org/"):
            orcid = orcid.replace("https://orcid.org/", "")
        
        # Get affiliation
        affiliation = "N/A"
        last_institution = author.get("last_known_institution", {})
        if last_institution:
            affiliation = last_institution.get("display_name", "N/A")
        
        if affiliation == "N/A":
            institutions = author.get("last_known_institutions", [])
            if institutions:
                affiliation = institutions[0].get("display_name", "N/A")
        
        works_count = author.get("works_count", 0)
        cited_by_count = author.get("cited_by_count", 0)
        h_index = author.get("summary_stats", {}).get("h_index", 0)
        
        print(f"\n{i}. {display_name}")
        print(f"   🆔 ORCID: {orcid}")
        print(f"   📍 Affiliation: {affiliation}")
        print(f"   📊 Papers: {works_count} | 📈 Citations: {cited_by_count} | 🎯 h-index: {h_index}")
    
    print("\n" + "=" * 80)
    
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

def extract_coauthors(authorships: List[dict], main_author_id: str) -> List[Dict]:
    """Extract co-authors with their affiliations."""
    coauthors = []
    
    for authorship in authorships:
        author_info = authorship.get("author", {})
        author_id = author_info.get("id", "")
        
        # Skip the main author
        if author_id == main_author_id:
            continue
        
        # Get author name
        author_name = author_info.get("display_name", "Unknown")
        
        # Get institutions
        institutions = authorship.get("institutions", [])
        affiliations = [inst.get("display_name", "Unknown") for inst in institutions]
        
        coauthors.append({
            "name": author_name,
            "affiliations": affiliations if affiliations else ["Unknown"]
        })
    
    return coauthors

def fetch_all_openalex_papers(author_id: str, batch_size: int = 100, max_papers: Optional[int] = None):
    """Fetch all papers for a specific author ID with co-author information."""
    all_papers = []
    cursor = "*"
    has_more = True
    
    print(f"📚 Fetching all papers for author (this may take a while for prolific authors)...")
    
    while has_more:
        url = f"https://api.openalex.org/works?filter=authorships.author.id:{author_id}&sort=cited_by_count:desc&per-page={batch_size}&cursor={cursor}"
        
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            
            papers_data = data.get("results", [])
            if not papers_data:
                has_more = False
                break
            
            for item in papers_data:
                # Decode inverted abstract
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
                
                # Get venue
                primary_location = item.get("primary_location", {})
                venue = ""
                if primary_location:
                    source = primary_location.get("source", {})
                    if source:
                        venue = source.get("display_name", "")
                
                if not venue:
                    venue = item.get("host_venue", {}).get("display_name", "")
                
                # Get title
                title = item.get("display_name") or item.get("title", "Untitled")
                
                # Extract co-authors
                authorships = item.get("authorships", [])
                coauthors = extract_coauthors(authorships, author_id)
                
                # Extract arXiv ID if available
                arxiv_id = None
                ids = item.get("ids", {})
                if ids:
                    arxiv_url = ids.get("arxiv")
                    if arxiv_url:
                        match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', arxiv_url)
                        if match:
                            arxiv_id = match.group(1)
                
                # Get DOI
                doi = item.get("doi") or ""
                if doi:
                    doi = doi.replace("https://doi.org/", "")
                
                all_papers.append({
                    "title": title,
                    "year": item.get("publication_year", "N/A"),
                    "venue": venue if venue else "N/A",
                    "cited_by_count": item.get("cited_by_count", 0),
                    "abstract": abstract,
                    "coauthors": coauthors,
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                    "openalex_id": item.get("id", "")
                })
            
            # Check if we have more results
            meta = data.get("meta", {})
            cursor = meta.get("next_cursor", "")
            has_more = bool(cursor)
            
            # Apply max_papers limit if specified
            if max_papers and len(all_papers) >= max_papers:
                all_papers = all_papers[:max_papers]
                has_more = False
            
            # Progress indicator
            print(f"   Fetched {len(all_papers)} papers so far...")
            
        except Exception as e:
            print(f"⚠️  Error fetching papers: {e}")
            break
    
    print(f"✅ Total papers fetched: {len(all_papers)}")
    return all_papers

# -----------------------------
# Unpaywall/Open Access Fetching
# -----------------------------
async def fetch_unpaywall(session, doi: str) -> Optional[str]:
    """Fetch open access version of paper via Unpaywall."""
    if not doi:
        return None
    
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=research@example.com"
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            
            data = await resp.json()
            
            # Check if open access version is available
            if data.get("oa_status") in ["green", "gold", "hybrid"]:
                oa_location = data.get("best_oa_location", {})
                if oa_location:
                    pdf_url = oa_location.get("url_for_pdf")
                    if pdf_url:
                        # Download the PDF
                        async with session.get(pdf_url) as pdf_resp:
                            if pdf_resp.status == 200:
                                pdf_data = await pdf_resp.read()
                                text = extract_text_from_pdf(pdf_data)
                                if text:
                                    return text
    except Exception as e:
        print(f"⚠️  Unpaywall fetch failed for DOI {doi}: {e}")
    
    return None

# -----------------------------
# Crossref Fetching
# -----------------------------
async def fetch_crossref_data(session, doi: str) -> Dict:
    """Fetch additional metadata from Crossref."""
    if not doi:
        return {}
    
    try:
        url = f"https://api.crossref.org/works/{doi}"
        async with session.get(url) as resp:
            if resp.status != 200:
                return {}
            
            data = await resp.json()
            message = data.get("message", {})
            
            # Safely extract fields with proper checks
            title_list = message.get("title", [])
            title = " ".join(title_list) if title_list else ""
            
            container_title_list = message.get("container-title", [])
            container_title = container_title_list[0] if container_title_list else ""
            
            date_parts = message.get("published-print", {}).get("date-parts", [[]])
            published = date_parts[0][0] if date_parts and date_parts[0] else ""
            
            return {
                "abstract": message.get("abstract", ""),
                "title": title,
                "published": published,
                "container_title": container_title
            }
    except Exception as e:
        print(f"⚠️  Crossref fetch failed for DOI {doi}: {e}")
    
    return {}

# -----------------------------
# arXiv Full Text Fetching
# -----------------------------
async def fetch_arxiv_pdf(session, arxiv_id: str) -> Optional[str]:
    """Download and extract text from arXiv PDF."""
    if not arxiv_id:
        return None
    
    try:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        async with session.get(pdf_url) as resp:
            if resp.status != 200:
                return None
            
            pdf_data = await resp.read()
            text = extract_text_from_pdf(pdf_data)
            if text:
                return text
                
    except Exception as e:
        print(f"⚠️  arXiv PDF fetch failed for {arxiv_id}: {e}")
    
    return None

async def fetch_arxiv_fulltext(session, arxiv_id: str) -> Optional[str]:
    """Fetch full text from arXiv, trying PDF first then falling back to abstract."""
    if not arxiv_id:
        return None
    
    # First try to get the PDF
    pdf_text = await fetch_arxiv_pdf(session, arxiv_id)
    if pdf_text:
        return pdf_text
    
    # Fallback to abstract
    try:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            
            xml_content = await resp.text()
            root = ET.fromstring(xml_content)
            
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            
            if entry is not None:
                summary = entry.find('atom:summary', ns)
                if summary is not None and summary.text:
                    return summary.text.strip()
    except Exception as e:
        print(f"⚠️  arXiv fetch failed for {arxiv_id}: {e}")
    
    return None

# -----------------------------
# Semantic Scholar Fetching
# -----------------------------
async def fetch_semantic_data(session, title: str) -> Dict:
    """Fetch abstract and TL;DR from Semantic Scholar."""
    try:
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": title, "limit": 1, "fields": "title,abstract,tldr"}
        async with session.get(search_url, params=params) as resp:
            if resp.status != 200:
                return {}
            data = await resp.json()
            papers = data.get("data", [])
            if papers:
                paper = papers[0]
                return {
                    "abstract": paper.get("abstract", ""),
                    "tldr": paper.get("tldr", {}).get("text", "")
                }
    except Exception:
        pass
    return {}

# -----------------------------
# Enhanced Content Enrichment with Deduplication
# -----------------------------
async def enrich_papers_with_content(papers: List[dict], max_concurrent: int = 5) -> List[dict]:
    """Enrich papers with full text from multiple sources with deduplication."""
    async with aiohttp.ClientSession() as session:
        enriched_papers = []
        
        for i in range(0, len(papers), max_concurrent):
            batch = papers[i:i+max_concurrent]
            
            # Create tasks for all data sources
            tasks = []
            
            for p in batch:
                # arXiv
                tasks.append(fetch_arxiv_fulltext(session, p.get("arxiv_id")))
                
                # Semantic Scholar
                tasks.append(fetch_semantic_data(session, p["title"]))
                
                # Unpaywall (if DOI available)
                tasks.append(fetch_unpaywall(session, p.get("doi")))
                
                # Crossref (if DOI available)
                tasks.append(fetch_crossref_data(session, p.get("doi")))
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for each paper
            for j, paper in enumerate(batch):
                content_sources = []  # List of (content, source) tuples
                
                # arXiv result
                arxiv_result = results[j*4]
                if isinstance(arxiv_result, str) and arxiv_result:
                    source_type = "arXiv PDF" if len(arxiv_result) > 1000 else "arXiv Abstract"
                    content_sources.append((arxiv_result, source_type))
                
                # Semantic Scholar result
                ss_result = results[j*4 + 1]
                if isinstance(ss_result, dict):
                    if ss_result.get("abstract"):
                        content_sources.append((ss_result["abstract"], "Semantic Scholar"))
                    if ss_result.get("tldr"):
                        tldr_text = f"Summary: {ss_result['tldr']}"
                        content_sources.append((tldr_text, "Semantic Scholar TL;DR"))
                        paper["tldr"] = ss_result["tldr"]
                
                # Unpaywall result
                unpaywall_result = results[j*4 + 2]
                if isinstance(unpaywall_result, str) and unpaywall_result:
                    content_sources.append((unpaywall_result, "Unpaywall OA"))
                
                # Crossref result
                crossref_result = results[j*4 + 3]
                if isinstance(crossref_result, dict):
                    if crossref_result.get("abstract"):
                        content_sources.append((crossref_result["abstract"], "Crossref"))
                
                # Add OpenAlex abstract
                if paper["abstract"]:
                    content_sources.append((paper["abstract"], "OpenAlex"))
                
                # Deduplicate content
                unique_content = deduplicate_content(content_sources)
                
                # Combine unique content
                combined_content = []
                sources = []
                for content, source in unique_content:
                    combined_content.append(content)
                    sources.append(source)
                
                paper["full_content"] = "\n\n".join(combined_content)
                paper["has_fulltext"] = bool(combined_content)
                paper["content_source"] = ", ".join(sources) if sources else "None"
                paper["content_sources"] = sources  # Keep detailed source info
                
                enriched_papers.append(paper)
            
            # Progress indicator
            print(f"   Processed {min(i+max_concurrent, len(papers))}/{len(papers)} papers...")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
    
    return enriched_papers

# -----------------------------
# Rule-based Summary Fallback
# -----------------------------
def rule_based_summary(author_name: str, papers: List[dict]) -> str:
    """Generate rule-based summary from paper content."""
    all_text = " ".join([p.get("full_content", "") for p in papers])
    words = re.findall(r"\b[a-zA-Z]{5,}\b", all_text.lower())
    counter = Counter(words)
    
    stopwords = {"based", "using", "paper", "approach", "method", "system", "systems", 
                 "research", "study", "results", "proposed", "present", "provide"}
    keywords = [w for w, _ in counter.most_common(20) if w not in stopwords][:10]
    
    summary = f"{author_name} has published {len(papers)} papers. "
    summary += f"Main research areas include: {', '.join(keywords)}. "
    
    total_citations = sum(p.get("cited_by_count", 0) for p in papers)
    summary += f"These papers have received {total_citations} citations in total."
    
    return summary

# -----------------------------
# LLM Summary Generation
# -----------------------------
def generate_paper_summary(paper: dict, max_tokens: int = 300) -> str:
    """Generate a summary for an individual paper using LLM if full-text available."""
    title = paper.get("title", "Untitled")
    content = paper.get("full_content", "") or paper.get("abstract", "")
    
    if not content or len(content) < 100:
        return "No content available for summarization."
    
    # Use LLM for full-text papers
    if paper.get("has_fulltext") and len(content) > 1000:
        prompt = f"""Summarize the following research paper in 3-4 sentences, focusing on:
1. Main contribution/novelty
2. Methodology/approach
3. Key results/findings

Paper: {title}

Content:
{content[:2000]}

Provide a concise summary:"""
        
        try:
            summary = generate_with_groq(prompt, model=GROQ_MODEL, max_tokens=max_tokens, temperature=0.2)
            return summary.strip()
        except Exception as e:
            # Fallback to abstract
            return content[:600] + "..." if len(content) > 600 else content
    else:
        # Return abstract for papers without full-text
        return content[:600] + "..." if len(content) > 600 else content


def classify_paper_domains(papers: List[dict], batch_size: int = 10) -> List[dict]:
    """Classify papers into domains using LLM.
    
    Returns papers with added 'domains' field (list of domain strings).
    """
    # Domain list (expand as needed)
    allowed_domains = [
        "machine learning", "deep learning", "natural language processing",
        "computer vision", "edge computing", "cloud computing", 
        "distributed systems", "networking", "security", "IoT",
        "optimization", "algorithms", "theory", "databases",
        "software engineering", "human-computer interaction", "robotics",
        "bioinformatics", "healthcare", "other"
    ]
    
    print(f"🏷️  Classifying {len(papers)} papers into domains using LLM... (cache: {DOMAIN_CACHE_FILE})")

    cache = load_domain_cache()

    for i in range(0, len(papers), batch_size):
        batch = papers[i:i+batch_size]

        # Build batch items for papers not present in cache
        items = []
        abs_indices = []
        for j, p in enumerate(batch):
            abs_idx = i + j
            # Determine a cache key: prefer OpenAlex id, then DOI, then title hash
            key = p.get("openalex_id") or p.get("doi") or hashlib.md5((p.get("title","") or "").encode()).hexdigest()

            if key in cache:
                # assign cached values immediately
                try:
                    papers[abs_idx]["domains"] = cache[key].get("domains", ["other"])[:2]
                    papers[abs_idx]["domain_confidence"] = cache[key].get("confidence", 0.0)
                except Exception:
                    papers[abs_idx]["domains"] = ["other"]
                continue

            title = p.get("title", "")
            abstract = p.get("abstract", "")[:500]
            items.append({"id": abs_idx, "title": title, "text": abstract})
            abs_indices.append((abs_idx, key))

        if not items:
            # nothing to call LLM for in this batch
            print(f"   Skipped batch {i//batch_size + 1}: all cached")
            continue

        items_json = json.dumps(items, indent=2)
        prompt = f"""You are a research paper classifier. Given papers (id, title, text), assign each to 1-2 domains from this list:
{', '.join(allowed_domains)}

Return ONLY valid JSON array: [{{"id": <id>, "domains": ["domain1", "domain2"], "confidence": 0.0-1.0}}]

Papers:
{items_json}

Output JSON:"""

        try:
            response = generate_with_groq(prompt, model=GROQ_MODEL, max_tokens=800, temperature=0.1)
            result = json.loads(response.strip())

            # Assign domains to papers and update cache
            for item in result:
                paper_idx = item.get("id", -1)
                domains = item.get("domains", ["other"])[:2]
                confidence = item.get("confidence", 0.0)
                if 0 <= paper_idx < len(papers):
                    papers[paper_idx]["domains"] = domains
                    papers[paper_idx]["domain_confidence"] = confidence

                    # find the cache key for this abs index
                    for abs_idx, key in abs_indices:
                        if abs_idx == paper_idx:
                            cache[key] = {"domains": domains, "confidence": confidence}
                            break

        except Exception as e:
            print(f"⚠️  Domain classification failed for batch {i//batch_size + 1}: {e}")
            # Fallback: assign "other" for uncached items
            for abs_idx, key in abs_indices:
                if "domains" not in papers[abs_idx]:
                    papers[abs_idx]["domains"] = ["other"]
                    cache[key] = {"domains": ["other"], "confidence": 0.0}

        # Persist cache after each batch to avoid redoing work on interruption
        try:
            save_domain_cache(cache)
        except Exception:
            pass

        print(f"   Classified {min(i+batch_size, len(papers))}/{len(papers)} papers...")
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(papers):
            time.sleep(1)

    return papers


def compute_publication_stats(papers: List[dict], author_info: dict) -> dict:
    """Compute publication velocity, yearly distribution, and collaboration patterns."""
    stats = {
        "total_papers": len(papers),
        "years_active": 0,
        "papers_per_year": {},
        "publication_velocity": 0.0,
        "top_collaborators": [],
        "collaboration_stats": {}
    }
    
    # Yearly distribution
    years = [p.get("year") for p in papers if isinstance(p.get("year"), int)]
    if years:
        min_year = min(years)
        max_year = max(years)
        stats["years_active"] = max_year - min_year + 1
        stats["publication_velocity"] = len(papers) / stats["years_active"] if stats["years_active"] > 0 else 0
        
        for year in years:
            stats["papers_per_year"][year] = stats["papers_per_year"].get(year, 0) + 1
    
    # Collaboration patterns
    coauthor_counts = Counter()
    for paper in papers:
        coauthors = paper.get("coauthors", [])
        for ca in coauthors:
            coauthor_counts[ca["name"]] += 1
    
    # Top 10 collaborators
    stats["top_collaborators"] = coauthor_counts.most_common(10)
    stats["collaboration_stats"] = {
        "total_coauthors": len(coauthor_counts),
        "avg_coauthors_per_paper": sum(len(p.get("coauthors", [])) for p in papers) / len(papers) if papers else 0
    }
    
    return stats


def generate_author_summary(author_name: str, author_info: dict, papers: List[dict]) -> str:
    """Generate comprehensive author summary using advanced LLM."""
    # Prepare paper information - use a representative sample for LLM processing
    sample_size = min(20, len(papers))
    top_papers = sorted(papers, key=lambda x: x.get("cited_by_count", 0), reverse=True)[:sample_size]
    
    papers_text = []
    for i, p in enumerate(top_papers, 1):
        content = p.get("full_content", "")[:800]
        
        # Format co-authors
        coauthors_str = ""
        if p.get("coauthors"):
            coauthor_names = [ca["name"] for ca in p["coauthors"][:3]]
            if len(p["coauthors"]) > 3:
                coauthors_str = f"Co-authors: {', '.join(coauthor_names)}, and {len(p['coauthors']) - 3} others"
            else:
                coauthors_str = f"Co-authors: {', '.join(coauthor_names)}"
        
        paper_info = f"{i}. {p['title']} ({p.get('year', 'N/A')})\n"
        paper_info += f"   Venue: {p.get('venue', 'N/A')} | Citations: {p.get('cited_by_count', 0)}\n"
        if coauthors_str:
            paper_info += f"   {coauthors_str}\n"
        paper_info += f"   Content: {content}"
        
        papers_text.append(paper_info)
    
    combined_text = "\n\n".join(papers_text)
    
    # Get affiliation
    affiliation_name = "Unknown"
    last_institution = author_info.get("last_known_institution", {})
    if last_institution:
        affiliation_name = last_institution.get("display_name", "Unknown")
    else:
        institutions = author_info.get("last_known_institutions", [])
        if institutions:
            affiliation_name = institutions[0].get("display_name", "Unknown")
    
    total_works = author_info.get("works_count", 0)
    total_citations = author_info.get("cited_by_count", 0)
    h_index = author_info.get("summary_stats", {}).get("h_index", 0)
    
    prompt = f"""You are an expert research analyst. Analyze the research profile of {author_name}, affiliated with {affiliation_name}.

Author Metrics:
- Total Publications: {total_works}
- Total Citations: {total_citations}
- h-index: {h_index}

Based on the following top papers (with full content when available), write a comprehensive 3-4 paragraph research summary covering:

1. **Main Research Areas**: Identify primary domains, methodologies, and theoretical frameworks
2. **Key Contributions**: Highlight novel contributions, breakthrough findings, and impact
3. **Research Evolution**: Note any evolution in research focus over time
4. **Collaboration Patterns**: Comment on co-authorship and interdisciplinary work
5. **Impact & Significance**: Assess the broader impact on the field

Top Papers:
{combined_text}

Write a detailed, insightful summary of {author_name}'s research contributions:"""

    try:
        print(f"🤖 Generating summary with {GROQ_MODEL} via GroqCloud...")
        try:
            summary = generate_with_groq(prompt, model=GROQ_MODEL, max_tokens=1024, temperature=0.2)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"⚠️  Groq API rate limit exceeded after retries")
                print(f"💡 Tip: Wait a minute and try again, or use a different API key")
            else:
                print(f"⚠️  Groq call failed: {e}")
            print("📝 Using rule-based summary instead...\n")
            return rule_based_summary(author_name, papers)
        except Exception as e:
            # If Groq call fails, fall back to rule-based
            print(f"⚠️  Groq call failed: {e}")
            print("📝 Using rule-based summary instead...\n")
            return rule_based_summary(author_name, papers)

        if not summary or not str(summary).strip():
            print("⚠️  Empty summary from Groq")
            print("📝 Using rule-based summary instead...\n")
            return rule_based_summary(author_name, papers)

        return str(summary).strip()

    except Exception as e:
        print(f"⚠️  LLM failed unexpectedly: {e}")
        print("📝 Using rule-based summary instead...\n")
        return rule_based_summary(author_name, papers)

# -----------------------------
# Main Function
# -----------------------------
def main():
    print("🔍 Enhanced Author Profile System with Multiple Data Sources and Deduplication")
    print("Data sources: OpenAlex, arXiv, Semantic Scholar, Unpaywall, Crossref")
    print("Features: Automatic duplicate removal from multiple sources")
    print("Note: For PDF extraction, install: pip install PyPDF2 pdfplumber")
    print()
    
    # Safe input helper to allow non-interactive runs (returns default on EOF)
    def safe_input(prompt: str, default: str = "") -> str:
        try:
            return input(prompt)
        except EOFError:
            return default

    # Step 0: Ask search method
    search_method = safe_input("Search by (1) Name or (2) ORCID? Enter 1 or 2: ", "1").strip()
    
    author_info = None
    
    if search_method == "2":
        # ORCID search
        orcid = safe_input("Enter ORCID (e.g., 0000-0002-1825-0097): ", "").strip()
        print(f"\n📋 Searching by ORCID: {orcid}")
        author_info = fetch_author_by_orcid(orcid)
        
        if not author_info:
            print("❌ No author found with that ORCID")
            return
        
        print(f"✅ Found: {author_info.get('display_name', 'Unknown')}")
    else:
        # Name search
        author_name = safe_input("Enter author name: ", "").strip()
        
        # Step 1: Fetch author candidates
        print(f"\n📋 Searching for: {author_name}")
        authors = fetch_author_candidates(author_name)
        
        if not authors:
            print("❌ No authors found in OpenAlex")
            return
        
        # Step 2: Select author
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
    display_name = author_info.get("display_name", "Unknown")
    # Note: works_count is from cached metadata and may differ slightly from actual fetch
    estimated_papers = author_info.get("works_count", 0)
    
    # Ask if user wants all papers or a sample
    fetch_all_input = safe_input(f"\n📚 Fetch all papers (~{estimated_papers} estimated)? This may take a while. (y/N): ", "n").strip()
    try:
        fetch_all = fetch_all_input.lower() == 'y'
    except Exception:
        fetch_all = False
    
    # Step 3: Fetch papers with co-authors
    if fetch_all:
        papers = fetch_all_openalex_papers(author_id)
    else:
        max_papers = safe_input("How many papers to fetch? (default 20): ", "20").strip()
        try:
            max_papers = int(max_papers) if max_papers else 20
        except ValueError:
            max_papers = 20

        print(f"\n📚 Fetching top {max_papers} papers with co-author information...")
        papers = fetch_all_openalex_papers(author_id, max_papers=max_papers)
    
    if not papers:
        print("❌ No papers found for this author")
        return
    
    # Step 4: Enrich with full content from multiple sources
    print("🔄 Enriching with content from multiple sources (with deduplication)...")
    papers = asyncio.run(enrich_papers_with_content(papers))
    
    # Count sources and duplicates removed
    source_counts = {}
    fulltext_count = 0
    
    for p in papers:
        if p.get("has_fulltext"):
            fulltext_count += 1
        
        # Count sources
        if p.get("content_sources"):
            for source in p["content_sources"]:
                source_counts[source] = source_counts.get(source, 0) + 1
    
    print(f"✅ Found full text for {fulltext_count}/{len(papers)} papers")
    if source_counts:
        print("   Sources after deduplication:")
        for source, count in source_counts.items():
            print(f"   - {source}: {count} papers")
    
    # Step 4a: Classify papers into domains
    papers = classify_paper_domains(papers)
    
    # Step 4b: Compute publication statistics
    print("\n📊 Computing publication statistics...")
    pub_stats = compute_publication_stats(papers, author_info)
    
    # Step 5: Generate LLM summary
    print(f"\n🤖 Generating comprehensive research summary...")
    summary = generate_author_summary(display_name, author_info, papers)
    
    # -----------------------------
    # Display Results
    # -----------------------------
    print("\n" + "=" * 80)
    print(f"AUTHOR PROFILE: {display_name}")
    print("=" * 80)
    
    # Get ORCID
    orcid = author_info.get("orcid", "N/A")
    if orcid and orcid.startswith("https://orcid.org/"):
        orcid = orcid.replace("https://orcid.org/", "")
    
    # Get affiliation
    affiliation_name = "N/A"
    last_institution = author_info.get("last_known_institution", {})
    if last_institution:
        affiliation_name = last_institution.get("display_name", "N/A")
    else:
        institutions = author_info.get("last_known_institutions", [])
        if institutions:
            affiliation_name = institutions[0].get("display_name", "N/A")
    
    print(f"🆔 ORCID: {orcid}")
    print(f"📍 Affiliation: {affiliation_name}")
    print(f"📊 Total Publications: {author_info.get('works_count', 0)}")
    print(f"📈 Total Citations: {author_info.get('cited_by_count', 0)}")
    print(f"🎯 h-index: {author_info.get('summary_stats', {}).get('h_index', 0)}")
    
    print("\n" + "=" * 80)
    print("📊 PUBLICATION STATISTICS")
    print("=" * 80)
    print(f"Years Active: {pub_stats['years_active']}")
    print(f"Publication Velocity: {pub_stats['publication_velocity']:.2f} papers/year")
    print(f"\nPapers per Year:")
    for year in sorted(pub_stats['papers_per_year'].keys(), reverse=True)[:10]:
        count = pub_stats['papers_per_year'][year]
        print(f"  {year}: {count} papers")
    
    print(f"\n👥 Collaboration Patterns:")
    print(f"Total Unique Collaborators: {pub_stats['collaboration_stats']['total_coauthors']}")
    print(f"Average Co-authors per Paper: {pub_stats['collaboration_stats']['avg_coauthors_per_paper']:.1f}")
    print(f"\nTop 10 Collaborators:")
    for name, count in pub_stats['top_collaborators'][:10]:
        print(f"  {name}: {count} papers")
    
    print("\n" + "=" * 80)
    print("🧠 RESEARCH SUMMARY")
    print("=" * 80)
    print(summary)
    
    print("\n" + "=" * 80)
    print(f"📚 PAPERS BY DOMAIN ({len(papers)} total)")
    print("=" * 80)
    
    # Group papers by domain
    domain_groups = {}
    for paper in papers:
        domains = paper.get("domains", ["other"])
        primary_domain = domains[0] if domains else "other"
        if primary_domain not in domain_groups:
            domain_groups[primary_domain] = []
        domain_groups[primary_domain].append(paper)
    
    # Sort domains by paper count (descending), but move "other" to the end
    sorted_domains = sorted(domain_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Move "other" domain to the end
    other_domain = None
    filtered_domains = []
    for domain, papers in sorted_domains:
        if domain.lower() == "other":
            other_domain = (domain, papers)
        else:
            filtered_domains.append((domain, papers))
    
    # Append "other" at the end if it exists
    if other_domain:
        filtered_domains.append(other_domain)
    
    sorted_domains = filtered_domains
    
    print(f"\n📊 Found {len(sorted_domains)} domains. Showing top papers per domain.\n")
    
    # Display domains one at a time with pagination
    for domain_idx, (domain, domain_papers) in enumerate(sorted_domains, 1):
        print(f"\n{'='*80}")
        print(f"📂 DOMAIN {domain_idx}/{len(sorted_domains)}: {domain.upper()} ({len(domain_papers)} papers)")
        print(f"{'='*80}")
        
        # Sort by citations within domain
        domain_papers.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
        
        for i, p in enumerate(domain_papers[:10], 1):  # Show top 10 per domain
            print(f"\n{i}. {p['title']}")
            print(f"   📅 Year: {p.get('year', 'N/A')} | 📊 Citations: {p.get('cited_by_count', 0)}")
            print(f"   🏛️  Venue: {p.get('venue', 'N/A')}")
            
            # Show content source
            if p.get("content_source"):
                print(f"   📄 Content Source: {p['content_source']}")
            
            # Show co-authors with affiliations
            if p.get("coauthors"):
                print(f"   👥 Co-authors ({len(p['coauthors'])} total):")
                # Show top 5 co-authors with affiliations
                for idx, ca in enumerate(p["coauthors"][:5], 1):
                    name = ca.get("name", "Unknown")
                    affiliations = ca.get("affiliations", ["Unknown"])
                    affil_str = ", ".join(affiliations[:2])  # Show up to 2 affiliations
                    print(f"      {idx}. {name} ({affil_str})")
                if len(p["coauthors"]) > 5:
                    print(f"      ... and {len(p['coauthors']) - 5} more co-authors")
            
            if p.get("arxiv_id"):
                print(f"   📄 arXiv: {p['arxiv_id']}")
            if p.get("doi"):
                print(f"   🔗 DOI: {p['doi']}")
            
            # Generate and show paper summary
            print(f"   📝 Summary:")
            paper_summary = generate_paper_summary(p, max_tokens=200)
            # Indent summary
            for line in paper_summary.split('\n'):
                print(f"      {line}")
        
        if len(domain_papers) > 10:
            print(f"\n   ... and {len(domain_papers) - 10} more papers in this domain")
        
        # Pause before next domain (except for last one)
        if domain_idx < len(sorted_domains):
            print(f"\n{'─'*80}")
            try:
                user_input = safe_input(f"Press Enter to see next domain ({domain_idx+1}/{len(sorted_domains)}) or 'q' to skip remaining: ", "")
                if user_input.strip().lower() == 'q':
                    remaining = len(sorted_domains) - domain_idx
                    print(f"\n⏭️  Skipping {remaining} remaining domain(s)...")
                    break
            except:
                pass  # Continue if input fails
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
