import asyncio
import aiohttp
import re
import os
import json
from typing import List, Dict, Optional, Tuple, Set
import hashlib

# --- PDF Processing Dependencies ---
# These are optional; the code will handle their absence.
try:
    import PyPDF2
    import pdfplumber
    import io
except ImportError:
    PyPDF2 = None
    pdfplumber = None
    io = None
    print("WARNING: PDF libraries not found. Run 'pip install PyPDF2 pdfplumber' for full PDF text extraction.")

# --- Configuration ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAILTO_EMAIL = os.environ.get("MAILTO_EMAIL", "hello@example.com") # Polite pool for OpenAlex

# --- Helper Functions (from your advanced script) ---
def sanitize_text(text: Optional[str]) -> str:
    if not text: return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text) # Remove XML/HTML tags
    text = re.sub(r"(?im)^.*copyright.*$", " ", text)
    text = re.sub(r"(?im)^.*all rights reserved.*$", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def trim_to_last_sentence(text: str) -> str:
    if not text: return text
    last_punc = max(text.rfind('.'), text.rfind('?'), text.rfind('!'))
    if last_punc != -1:
        return text[:last_punc + 1].strip()
    return text.strip()

def normalize_text(text: str) -> str:
    if not text: return ""
    return re.sub(r'\s+', ' ', text.strip()).lower()

def get_text_hash(text: str) -> str:
    return hashlib.md5(normalize_text(text).encode()).hexdigest()

def deduplicate_content(content_list: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    unique_content: List[Tuple[str, str]] = []
    seen_hashes: Set[str] = set()
    for content, source in content_list:
        if not content or not content.strip(): continue
        content_hash = get_text_hash(content)
        if content_hash not in seen_hashes:
            unique_content.append((content, source))
            seen_hashes.add(content_hash)
    return unique_content

# --- PDF Extraction ---
def extract_text_from_pdf(pdf_data: bytes) -> Optional[str]:
    if not pdfplumber or not PyPDF2 or not io: return None
    try:
        with io.BytesIO(pdf_data) as pdf_stream:
            with pdfplumber.open(pdf_stream) as pdf:
                return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    except Exception:
        try:
            with io.BytesIO(pdf_data) as pdf_stream:
                reader = PyPDF2.PdfReader(pdf_stream)
                return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except Exception:
            return None
    return None

# --- Asynchronous Data Fetching Layer ---
async def _fetch_json(session: aiohttp.ClientSession, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    try:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

async def fetch_unpaywall_text(session: aiohttp.ClientSession, doi: str) -> Optional[str]:
    if not doi: return None
    data = await _fetch_json(session, f"https://api.unpaywall.org/v2/{doi}", params={"email": MAILTO_EMAIL})
    if data and data.get("best_oa_location") and data["best_oa_location"].get("url_for_pdf"):
        pdf_url = data["best_oa_location"]["url_for_pdf"]
        try:
            async with session.get(pdf_url, timeout=30) as pdf_resp:
                if pdf_resp.status == 200:
                    return extract_text_from_pdf(await pdf_resp.read())
        except Exception:
            return None
    return None

async def fetch_semantic_scholar_data(session: aiohttp.ClientSession, title: str) -> Optional[Dict]:
    params = {"query": title, "limit": 1, "fields": "abstract,tldr"}
    data = await _fetch_json(session, "https://api.semanticscholar.org/graph/v1/paper/search", params)
    return data.get("data", [None])[0] if data else None

async def search_openalex_authors(session: aiohttp.ClientSession, name: str) -> List[Dict]:
    params = {"search": name, "per-page": 5, "mailto": MAILTO_EMAIL}
    data = await _fetch_json(session, "https://api.openalex.org/authors", params)
    return data.get("results", []) if data else []

async def fetch_openalex_papers_by_author_id(session: aiohttp.ClientSession, author_id: str, max_papers: int = 10) -> List[Dict]:
    params = {"filter": f"authorships.author.id:{author_id}", "sort": "cited_by_count:desc", "per-page": max_papers, "mailto": MAILTO_EMAIL}
    data = await _fetch_json(session, "https://api.openalex.org/works", params)
    return data.get("results", []) if data else []

async def fetch_paper_by_id(session: aiohttp.ClientSession, paper_id: str) -> Optional[Dict]:
    url = f"https://api.openalex.org/works/{paper_id}"
    params = {"mailto": MAILTO_EMAIL}
    return await _fetch_json(session, url, params)

# --- Core Logic: Enrichment and Summarization ---
def process_paper_data(paper_data: Dict) -> Dict:
    """Extracts a clean abstract and other key fields from a raw OpenAlex work object."""
    abstract = ""
    inv_abstract = paper_data.get("abstract_inverted_index")
    if inv_abstract:
        try:
            max_pos = max(max(pos) for pos in inv_abstract.values())
            words = [""] * (max_pos + 1)
            for word, positions in inv_abstract.items():
                for pos in positions: words[pos] = word
            abstract = " ".join(words)
        except (ValueError, TypeError):
            abstract = "Abstract not available."
    
    paper_data['abstract'] = sanitize_text(abstract)
    return paper_data

async def enrich_paper_with_full_text(session: aiohttp.ClientSession, paper: Dict) -> Dict:
    """Gathers text from all sources for a single paper and deduplicates it."""
    content_sources: List[Tuple[str, str]] = []
    
    # 1. Base OpenAlex Abstract
    if paper.get("abstract"):
        content_sources.append((paper["abstract"], "OpenAlex"))
        
    # 2. Fetch from other sources concurrently
    doi = paper.get("ids", {}).get("doi", "").replace("https://doi.org/", "")
    title = paper.get("title", "")
    
    tasks = [
        fetch_unpaywall_text(session, doi),
        fetch_semantic_scholar_data(session, title)
    ]
    results = await asyncio.gather(*tasks)
    
    # Process results
    unpaywall_text, ss_data = results
    if unpaywall_text: content_sources.append((unpaywall_text, "Unpaywall PDF"))
    if ss_data and ss_data.get("abstract"): content_sources.append((ss_data["abstract"], "Semantic Scholar"))

    # Deduplicate and combine
    unique_content = deduplicate_content(content_sources)
    paper["full_content"] = "\n\n---\n\n".join(sanitize_text(c[0]) for c in unique_content)
    paper["content_sources"] = [c[1] for c in unique_content]
    
    return paper

async def generate_with_groq(session: aiohttp.ClientSession, prompt: str, max_tokens: int) -> Optional[str]:
    """Generates text using the Groq API asynchronously."""
    if not GROQ_API_KEY:
        print("Warning: GROQ_API_KEY not set. LLM summarization is disabled.")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    try:
        async with session.post(url, headers=headers, json=payload, timeout=120) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return None
        
async def generate_paper_summary(session: aiohttp.ClientSession, paper: Dict) -> str:
    """Generates the advanced, structured summary for a single paper."""
    content = paper.get("full_content") or paper.get("abstract")
    if not content or len(content) < 100:
        return "Not enough content available to generate a summary."

    prompt = f"""
    You are an expert research summarizer. Read the content below and produce a detailed, clear
    summary of this research paper. Provide a multi-paragraph summary (approx. 250-600 words)
    with the following labeled sections when applicable:

    - Background: Context of the work.
    - Main Contribution: The novel idea(s).
    - Methodology: How they did it.
    - Results/Findings: Key results and numbers.
    - Implications/Impact: Why it matters.

    Paper Title: {paper.get("title", "Untitled")}
    Content:
    {content[:4000]}
    
    Write the summary now, using the labeled sections above.
    """
    summary = await generate_with_groq(session, prompt, max_tokens=800)
    if summary:
        return trim_to_last_sentence(sanitize_text(summary))
    
    # Fallback to a simple excerpt if LLM fails
    return trim_to_last_sentence(content[:600]) + "..." if len(content) > 600 else content

async def generate_author_summary(session: aiohttp.ClientSession, author_info: Dict, papers: List[Dict]) -> str:
    """Generates the advanced, multi-faceted summary for an author."""
    papers_text = []
    for p in papers[:5]: # Use top 5 papers for the prompt
        content_snippet = (p.get("full_content") or p.get("abstract", ""))[:1500]
        papers_text.append(f"- Title: {p.get('title', 'N/A')}\n  Content: {content_snippet}...")

    # --- THE FIX IS HERE ---
    # 1. Pre-calculate the joined string with the newline character.
    papers_joined_text = "\n".join(papers_text)
    # --- END OF FIX ---

    prompt = f"""
    You are an expert research analyst. Analyze the research profile of {author_info['display_name']}.
    Affiliation: {author_info.get('last_known_institution', {}).get('display_name', 'N/A')}.
    Metrics: {author_info.get('works_count', 'N/A')} pubs, {author_info.get('cited_by_count', 'N/A')} citations.
    
    Based on their top papers below, write a comprehensive 3-paragraph summary covering:
    1. **Main Research Areas**: Key domains and methodologies.
    2. **Key Contributions**: Novel findings and impact.
    3. **Research Evolution**: Any notable shift in focus over time.

    Top Papers:
    {papers_joined_text} 
    
    Write a detailed, insightful summary:
    """
    summary = await generate_with_groq(session, prompt, max_tokens=1024)
    return summary or "Summary could not be generated. Check API key or service status."