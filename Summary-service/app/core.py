import asyncio
import aiohttp
import re
import os
import json
from typing import List, Dict, Optional, Tuple, Set, Counter
import hashlib
import xml.etree.ElementTree as ET

# --- PDF Processing Dependencies (Optional) ---
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
MAILTO_EMAIL = os.environ.get("MAILTO_EMAIL", "hello@example.com")

# --- Advanced Helper Functions (from script 2) ---
def sanitize_text(text: Optional[str]) -> str:
    if not text: return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
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

def is_duplicate(text1: str, text2: str, threshold: float = 0.9) -> bool:
    if not text1 or not text2: return False
    if get_text_hash(text1) == get_text_hash(text2): return True
    norm1, norm2 = normalize_text(text1), normalize_text(text2)
    if len(norm1) < 200 and len(norm2) < 200: return norm1 == norm2
    if norm1 in norm2 or norm2 in norm1: return True
    if len(norm1) > 100 and len(norm2) > 100:
        common_words = set(norm1.split()) & set(norm2.split())
        total_words = set(norm1.split()) | set(norm2.split())
        if total_words:
            return (len(common_words) / len(total_words)) > threshold
    return False

def deduplicate_content(content_list: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    unique_content: List[Tuple[str, str]] = []
    if not content_list: return []
    for content, source in content_list:
        if not content or not content.strip(): continue
        is_dup = any(is_duplicate(content, existing_content) for existing_content, _ in unique_content)
        if not is_dup:
            unique_content.append((content, source))
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

# --- Asynchronous Data Fetching Layer (Expanded) ---
async def _fetch_json(session: aiohttp.ClientSession, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    try:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception:
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

async def fetch_crossref_data(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    if not doi: return None
    data = await _fetch_json(session, f"https://api.crossref.org/works/{doi}")
    if data and data.get("message"):
        return {"abstract": data["message"].get("abstract", "")}
    return None

async def fetch_arxiv_fulltext(session: aiohttp.ClientSession, arxiv_id: str) -> Optional[str]:
    if not arxiv_id: return None
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        async with session.get(pdf_url) as pdf_resp:
            if pdf_resp.status == 200:
                pdf_data = await pdf_resp.read()
                return extract_text_from_pdf(pdf_data)
    except Exception:
        pass # Fallback to abstract if PDF fails
    
    try:
        abs_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        async with session.get(abs_url) as resp:
            if resp.status == 200:
                xml_content = await resp.text()
                root = ET.fromstring(xml_content)
                entry = root.find('{http://www.w3.org/2005/Atom}entry')
                if entry:
                    summary = entry.find('{http://www.w3.org/2005/Atom}summary')
                    if summary is not None: return summary.text.strip()
    except Exception:
        return None
    return None


async def search_openalex_authors(session: aiohttp.ClientSession, name: str) -> List[Dict]:
    params = {"search": name, "per-page": 5, "mailto": MAILTO_EMAIL}
    data = await _fetch_json(session, "https://api.openalex.org/authors", params)
    return data.get("results", []) if data else []

async def fetch_openalex_papers_by_author_id(session: aiohttp.ClientSession, author_id: str, max_papers: int = 30) -> List[Dict]:
    params = {"filter": f"authorships.author.id:{author_id}", "sort": "cited_by_count:desc", "per-page": max_papers, "mailto": MAILTO_EMAIL}
    data = await _fetch_json(session, "https://api.openalex.org/works", params)
    return data.get("results", []) if data else []

async def fetch_paper_by_id(session: aiohttp.ClientSession, paper_id: str) -> Optional[Dict]:
    url = f"https://api.openalex.org/works/{paper_id}"
    params = {"mailto": MAILTO_EMAIL}
    return await _fetch_json(session, url, params)
async def fetch_author_by_id(session: aiohttp.ClientSession, id: str) -> Optional[Dict]:
    """
    Fetches a single author's full details from OpenAlex using their ID.
    """
    if not id.startswith("https://openalex.org/"):
         url = f"https://api.openalex.org/{id}"
    else:
         # Handle cases where the full URL might be passed
         url = id

    params = {"mailto": MAILTO_EMAIL}
    return await _fetch_json(session, f"https://api.openalex.org/{url}", params)
# --- Core Logic: Enrichment and Summarization ---
def process_paper_data(paper_data: Dict) -> Dict:
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
    
    # Extract IDs
    ids = paper_data.get("ids", {})
    paper_data["doi"] = ids.get("doi", "").replace("https://doi.org/", "")
    arxiv_url = ids.get("arxiv")
    if arxiv_url:
        match = re.search(r'arxiv\.org/abs/(\S+)', arxiv_url)
        paper_data["arxiv_id"] = match.group(1) if match else None
    else:
        paper_data["arxiv_id"] = None

    # Extract Co-authors
    coauthors = []
    main_author_id = None
    if paper_data.get("authorships"):
        main_author_id = paper_data["authorships"][0].get("author", {}).get("id")

    for authorship in paper_data.get("authorships", []):
        author_info = authorship.get("author", {})
        if author_info.get("id") != main_author_id:
             coauthors.append({"name": author_info.get("display_name", "Unknown")})
    paper_data["coauthors"] = coauthors

    return paper_data

async def enrich_paper_with_full_text(session: aiohttp.ClientSession, paper: Dict) -> Dict:
    content_sources: List[Tuple[str, str]] = []
    
    if paper.get("abstract"):
        content_sources.append((paper["abstract"], "OpenAlex"))
        
    doi = paper.get("doi")
    title = paper.get("title", "")
    arxiv_id = paper.get("arxiv_id")
    
    tasks = [
        fetch_unpaywall_text(session, doi),
        fetch_semantic_scholar_data(session, title),
        fetch_crossref_data(session, doi),
        fetch_arxiv_fulltext(session, arxiv_id)
    ]
    results = await asyncio.gather(*tasks)
    
    unpaywall_text, ss_data, crossref_data, arxiv_text = results
    
    if unpaywall_text: content_sources.append((unpaywall_text, "Unpaywall PDF"))
    if ss_data and ss_data.get("abstract"): content_sources.append((ss_data["abstract"], "Semantic Scholar"))
    if crossref_data and crossref_data.get("abstract"): content_sources.append((crossref_data["abstract"], "Crossref"))
    if arxiv_text: content_sources.append((arxiv_text, "arXiv"))

    unique_content = deduplicate_content(content_sources)
    paper["full_content"] = "\n\n---\n\n".join(sanitize_text(c[0]) for c in unique_content)
    paper["content_sources"] = [c[1] for c in unique_content]
    
    return paper

async def generate_with_groq(session: aiohttp.ClientSession, prompt: str, max_tokens: int) -> Optional[str]:
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
    except Exception:
        return None

def rule_based_summary(author_name: str, papers: List[Dict]) -> str:
    """Generate a rule-based summary as a fallback."""
    if not papers: return f"No papers were available to generate a summary for {author_name}."
    
    all_text = " ".join([p.get("full_content", p.get("abstract", "")) for p in papers])
    words = re.findall(r"\b[a-zA-Z]{5,}\b", all_text.lower())
    
    stopwords = {"based", "using", "paper", "approach", "method", "system", "research", "study", "results", "propose", "present", "provide", "model", "models"}
    
    counter = Counter(w for w in words if w not in stopwords)
    keywords = [w for w, _ in counter.most_common(10)]
    
    total_citations = sum(p.get("cited_by_count", 0) for p in papers)
    
    summary = (
        f"A rule-based analysis of the work by {author_name} indicates a focus on several key areas. "
        f"Across {len(papers)} analyzed publications, which have collectively received {total_citations} citations, "
        f"prominent keywords include: {', '.join(keywords)}. This suggests a strong concentration in these domains."
    )
    return summary
        
async def generate_paper_summary(session: aiohttp.ClientSession, paper: Dict) -> str:
    content = paper.get("full_content") or paper.get("abstract")
    if not content or len(content) < 100:
        return "Not enough content available to generate a summary."

    prompt = f"""
    You are an expert research summarizer. Read the content below and produce a detailed, clear summary of this research paper.
    Provide a multi-paragraph summary (approx. 250-600 words) with the following labeled sections when applicable:

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
    if summary and summary.strip():
        return trim_to_last_sentence(sanitize_text(summary))
    
    return trim_to_last_sentence(content[:600]) + "..." if len(content) > 600 else content

async def generate_author_summary(session: aiohttp.ClientSession, author_info: Dict, papers: List[Dict]) -> str:
    """Generates the advanced, multi-faceted summary for an author with a rule-based fallback."""
    if not papers:
        return rule_based_summary(author_info.get('display_name', 'this author'), papers)

    # --- CORRECTED PAPER SELECTION LOGIC ---
    # This now perfectly mirrors the CLI script's logic.
    sample_size = min(20, len(papers))
    num_cited = min(max(5, int(sample_size * 0.6)), sample_size)
    num_recent = sample_size - num_cited
    
    cited_sorted = sorted(papers, key=lambda p: p.get("cited_by_count", 0), reverse=True)
    recent_sorted = sorted(papers, key=lambda p: p.get("publication_year", 0) or 0, reverse=True)
    
    selected_papers = []
    seen_ids = set()

    # Step 1: Add the most highly-cited papers
    for p in cited_sorted:
        if len(selected_papers) >= num_cited:
            break
        paper_id = p.get('id')
        if paper_id and paper_id not in seen_ids:
            selected_papers.append(p)
            seen_ids.add(paper_id)
    
    # Step 2: Add the most recent papers, avoiding duplicates
    for p in recent_sorted:
        if len(selected_papers) >= sample_size:
            break
        paper_id = p.get('id')
        if paper_id and paper_id not in seen_ids:
            selected_papers.append(p)
            seen_ids.add(paper_id)

    # Build detailed context for the prompt
    papers_text = []
    for i, p in enumerate(selected_papers, 1):
        content_snippet = (p.get("full_content") or p.get("abstract", ""))[:2000]
        coauthors_str = ", ".join([ca["name"] for ca in p.get("coauthors", [])[:3]])
        
        paper_info = (
            f"{i}. {p.get('title', 'N/A')} ({p.get('publication_year', 'N/A')})\n"
            f"   Citations: {p.get('cited_by_count', 0)} | Co-authors: {coauthors_str}...\n"
            f"   Content: {content_snippet}..."
        )
        papers_text.append(paper_info)
    
    papers_joined_text = "\n\n".join(papers_text)
    
    affiliation = author_info.get('last_known_institution', {}).get('display_name', 'N/A')
    
    # Advanced Prompt
    prompt = f"""
    You are an expert research analyst. Analyze the research profile of {author_info['display_name']}, affiliated with {affiliation}.

    Author Metrics:
    - Publications: {author_info.get('works_count', 'N/A')}
    - Citations: {author_info.get('cited_by_count', 'N/A')}
    - h-index: {author_info.get('summary_stats', {}).get('h_index', 'N/A')}

    Based on their papers below, write a comprehensive 3-4 paragraph summary covering:
    1. **Main Research Areas**: Key domains, methodologies, and frameworks.
    2. **Key Contributions**: Novel findings and breakthroughs.
    3. **Research Evolution**: Shifts in focus over time.
    4. **Collaboration Patterns**: Note co-authorship and interdisciplinary work.
    5. **Impact & Significance**: Assess the broader impact on the field.

    Top Papers:
    {papers_joined_text} 
    
    Write a detailed, insightful summary of their research contributions:
    """
    
    try:
        summary = await generate_with_groq(session, prompt, max_tokens=1024)
        if summary and summary.strip():
            return sanitize_text(summary)
        else:
            print("LLM returned an empty summary. Using rule-based fallback.")
            return rule_based_summary(author_info['display_name'], papers)
    except Exception as e:
        print(f"LLM call failed ({e}). Using rule-based fallback.")
        return rule_based_summary(author_info['display_name'], papers)