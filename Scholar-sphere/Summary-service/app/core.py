#!/usr/bin/env python3
import requests
from keybert import KeyBERT
from transformers import pipeline
from datetime import datetime, timedelta
import json
import time
from collections import Counter
from difflib import SequenceMatcher

# ---------------- INITIALIZE MODELS ----------------
kw_model = KeyBERT(model="all-MiniLM-L6-v2")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# ---------------- HELPERS ----------------
def extract_keywords(text, top_n=10):
    if not text or len(text.strip()) < 20:
        return []
    try:
        keywords = kw_model.extract_keywords(text, top_n=top_n)
        return [kw for kw, _ in keywords]
    except Exception:
        return []

def titles_are_similar(title1, title2, threshold=0.85):
    """Check if two titles are similar using fuzzy matching."""
    if not title1 or not title2:
        return False
    
    # Normalize titles
    t1 = title1.lower().strip()
    t2 = title2.lower().strip()
    
    # Check if one is a substring of the other (handles subtitles)
    if t1 in t2 or t2 in t1:
        return True
    
    # Use SequenceMatcher for fuzzy comparison
    similarity = SequenceMatcher(None, t1, t2).ratio()
    return similarity >= threshold

def decode_openalex_abstract(abstract_index):
    """Convert OpenAlex abstract_inverted_index into plain text."""
    if not abstract_index:
        return ""
    position_word = {}
    for word, positions in abstract_index.items():
        for pos in positions:
            position_word[pos] = word
    return " ".join([position_word[i] for i in sorted(position_word.keys())])

OPENALEX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (AuthorProfileApp; +mailto:learn.et.bhavya@gmail.com)",
    "From":"learn.et.bhavya@gmail.com"
}

def api_call_with_retry(url, headers=None, max_retries=3):
    """Make API call with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            delay = 2 ** attempt
            if attempt > 0:
                print(f"⏳ Retry attempt {attempt + 1} after {delay}s delay...")
                time.sleep(delay)
            else:
                time.sleep(1)
            
            r = requests.get(url, headers=headers, timeout=30)
            
            if r.status_code == 429:
                print(f"⚠️  Rate limited. Waiting {delay * 2}s before retry...")
                time.sleep(delay * 2)
                continue
            
            r.raise_for_status()
            return r
            
        except requests.exceptions.Timeout:
            print(f"⚠️  Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
    
    return None

# ---------------- OPENALEX ----------------
def search_openalex_authors_by_name(name):
    """Search authors in OpenAlex by name."""
    try:
        url = f"https://api.openalex.org/authors?filter=display_name.search:{name}&per-page=5"
        print(f"\n🔍 DEBUG: OpenAlex name search URL: {url}")
        r = api_call_with_retry(url, headers=OPENALEX_HEADERS)
        if not r:
            return []
        results = r.json().get("results", [])
        print(f"✓ DEBUG: Found {len(results)} author(s) in OpenAlex by name")
        if results:
            for idx, author in enumerate(results[:3]):
                institutions = author.get("last_known_institutions", [])
                inst_names = [inst.get("display_name", "") for inst in institutions] if institutions else ["Unknown"]
                print(f"  {idx+1}. {author.get('display_name')} - ID: {author.get('id')} - Inst: {', '.join(inst_names[:2])}")
        return results
    except Exception as e:
        print(f"❌ DEBUG: OpenAlex author search error: {e}")
        return []

def fetch_openalex_papers(author_id, max_results=100, years_back=10):
    """
    Fetch papers for an author from OpenAlex by author ID.
    """
    try:
        if not author_id.startswith("https://openalex.org/"):
            author_full_id = f"https://openalex.org/{author_id}"
        else:
            author_full_id = author_id

        years_ago = datetime.now().year - years_back
        url = (
            f"https://api.openalex.org/works?"
            f"filter=authorships.author.id:{author_full_id},publication_year:>{years_ago}"
            f"&sort=cited_by_count:desc"
            f"&per-page={max_results}"
        )

        print(f"\n🔍 DEBUG: OpenAlex papers URL: {url}")
        
        r = api_call_with_retry(url, headers=OPENALEX_HEADERS)
        if not r:
            return []
        
        print(f"✓ DEBUG: OpenAlex papers response status: {r.status_code}")
        data = r.json()
        
        total_count = data.get('meta', {}).get('count', 0)
        results = data.get("results", [])
        print(f"✓ DEBUG: Found {len(results)} papers from OpenAlex (Total available: {total_count})")

        papers = []
        papers_with_abstract = 0
        papers_without_abstract = 0
        
        for w in results:
            venue = "Unknown"
            primary_location = w.get("primary_location")
            if primary_location and isinstance(primary_location, dict):
                source = primary_location.get("source")
                if source and isinstance(source, dict):
                    venue = source.get("display_name", "Unknown")

            abstract = decode_openalex_abstract(w.get("abstract_inverted_index"))
            if abstract:
                papers_with_abstract += 1
            else:
                papers_without_abstract += 1

            paper = {
                "title": w.get("title", "No title"),
                "venue": venue,
                "year": w.get("publication_year", "Unknown"),
                "abstract": abstract,
                "citations": w.get("cited_by_count", 0),
                "source": "OpenAlex",
                "doi": w.get("doi", "")
            }
            papers.append(paper)
            if len(papers) <= 3:
                abstract_status = "✓ Has abstract" if abstract else "✗ No abstract"
                print(f"  Paper {len(papers)}: {paper['year']} - {paper['title'][:60]}... [{abstract_status}]")

        print(f"📊 DEBUG: Papers with abstracts: {papers_with_abstract}, without: {papers_without_abstract}")
        return papers

    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response.status_code == 403:
            print(f"❌ DEBUG: OpenAlex 403 Forbidden - Rate limit reached")
        else:
            print(f"❌ DEBUG: OpenAlex fetch HTTP error: {e}")
        return []
    except Exception as e:
        print(f"❌ DEBUG: OpenAlex fetch error: {e}")
        return []

# ---------------- SEMANTIC SCHOLAR ----------------
def fetch_semantic_scholar_author(name):
    """Search authors by name in Semantic Scholar."""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/author/search?query={name}&fields=name,affiliations,externalIds,url,paperCount&limit=5"
        print(f"\n🔍 DEBUG: Semantic Scholar author URL: {url}")
        r = api_call_with_retry(url)
        if not r:
            return []
        data = r.json().get("data", [])
        print(f"✓ DEBUG: Found {len(data)} author(s) in Semantic Scholar")
        for idx, author in enumerate(data):
            affiliations = author.get("affiliations", [])
            aff_str = ", ".join(affiliations) if affiliations else "Unknown"
            print(f"  {idx+1}. {author.get('name')} - Papers: {author.get('paperCount', 'N/A')} - Aff: {aff_str} - ID: {author.get('authorId')}")
        return data
    except Exception as e:
        print(f"❌ DEBUG: Semantic Scholar author fetch error: {e}")
        return []

def fetch_semantic_scholar_papers(author_id, max_results=100):
    """Fetch papers from Semantic Scholar by author ID."""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers?fields=title,abstract,venue,year,citationCount&limit={max_results}"
        print(f"\n🔍 DEBUG: Semantic Scholar papers URL: {url}")
        r = api_call_with_retry(url)
        if not r:
            return []
        print(f"✓ DEBUG: Semantic Scholar papers response status: {r.status_code}")
        data = r.json()
        papers_data = data.get("data", [])
        print(f"✓ DEBUG: Found {len(papers_data)} papers from Semantic Scholar")
        
        papers = []
        papers_with_abstract = 0
        papers_without_abstract = 0
        
        for p in papers_data:
            abstract = p.get("abstract", "")
            if abstract:
                papers_with_abstract += 1
            else:
                papers_without_abstract += 1
                
            paper = {
                "title": p.get("title", "No title"),
                "venue": p.get("venue", "Unknown"),
                "year": p.get("year", "Unknown"),
                "abstract": abstract,
                "citations": p.get("citationCount", 0),
                "source": "SemanticScholar"
            }
            papers.append(paper)
            if len(papers) <= 3:
                abstract_status = "✓ Has abstract" if abstract else "✗ No abstract"
                print(f"  Paper {len(papers)}: {paper['year']} - {paper['title'][:60]}... [{abstract_status}]")
        
        print(f"📊 DEBUG: Papers with abstracts: {papers_with_abstract}, without: {papers_without_abstract}")
        return papers
    except Exception as e:
        print(f"❌ DEBUG: Semantic Scholar fetch error: {e}")
        return []

# ---------------- MERGE PAPERS ----------------
def merge_papers(openalex_papers, ss_papers):
    """Merge papers from OpenAlex and Semantic Scholar with fuzzy deduplication."""
    print(f"\n🔀 DEBUG: Merging {len(openalex_papers)} OpenAlex + {len(ss_papers)} Semantic Scholar papers")
    
    merged_list = []
    
    # Add all OpenAlex papers first
    for p in openalex_papers:
        if p.get("title"):
            merged_list.append(p)
    
    # Add Semantic Scholar papers, checking for duplicates
    duplicates_found = 0
    for ss_paper in ss_papers:
        ss_title = ss_paper.get("title", "").strip()
        if not ss_title:
            continue
        
        # Check if this paper is similar to any already in the list
        is_duplicate = False
        for idx, merged_paper in enumerate(merged_list):
            if titles_are_similar(ss_title, merged_paper.get("title", "")):
                is_duplicate = True
                duplicates_found += 1
                
                # If OpenAlex paper doesn't have abstract but SS does, use SS abstract
                if not merged_paper.get("abstract") and ss_paper.get("abstract"):
                    merged_list[idx]["abstract"] = ss_paper["abstract"]
                    print(f"  📝 Added abstract from SemanticScholar for: {ss_paper['title'][:60]}...")
                
                # Update citations if SS has more recent/higher count
                if ss_paper.get("citations", 0) > merged_paper.get("citations", 0):
                    merged_list[idx]["citations"] = ss_paper["citations"]
                
                break
        
        if not is_duplicate:
            merged_list.append(ss_paper)
    
    print(f"✓ DEBUG: After merging: {len(merged_list)} unique papers (removed {duplicates_found} duplicates)")
    
    # Count papers with/without abstracts
    with_abstract = sum(1 for p in merged_list if p.get("abstract"))
    without_abstract = len(merged_list) - with_abstract
    print(f"📊 DEBUG: Final stats - With abstracts: {with_abstract}, Without: {without_abstract}")
    
    return merged_list

# ---------------- KEYWORD ANALYSIS ----------------
def analyze_keywords(papers, top_n=20):
    """Extract and analyze keywords from papers with abstracts."""
    all_keywords = []
    papers_analyzed = 0
    
    for paper in papers:
        abstract = paper.get("abstract", "")
        if abstract and len(abstract.strip()) > 50:
            keywords = extract_keywords(abstract, top_n=5)
            all_keywords.extend(keywords)
            papers_analyzed += 1
    
    print(f"🔑 DEBUG: Extracted keywords from {papers_analyzed} papers with abstracts")
    
    keyword_counts = Counter(all_keywords)
    top_keywords = [kw for kw, count in keyword_counts.most_common(top_n)]
    
    return top_keywords

# ---------------- AUTHOR SUMMARY ----------------
def generate_author_summary(author_name, papers, affiliations=[]):
    """Generate a template-based research summary."""
    if not papers:
        return "No papers found."

    total_papers = len(papers)
    total_citations = sum(p.get("citations", 0) for p in papers)
    papers_with_abstracts = sum(1 for p in papers if p.get("abstract"))
    
    years = [p.get("year") for p in papers if isinstance(p.get("year"), int)]
    year_range = f"{min(years)}-{max(years)}" if years else "Unknown"
    
    venues = [p.get("venue") for p in papers if p.get("venue") and p.get("venue") != "Unknown"]
    top_venues = [v for v, c in Counter(venues).most_common(5)]
    
    keywords = analyze_keywords(papers, top_n=15)
    
    summary = f"""
Research Profile:
- Total Papers: {total_papers} (spanning {year_range})
- Total Citations: {total_citations}
- Papers with Abstracts Available: {papers_with_abstracts}
- Primary Research Areas: {', '.join(keywords[:10]) if keywords else 'N/A'}
- Frequent Publication Venues: {', '.join(top_venues[:3]) if top_venues else 'N/A'}
"""
    
    return summary.strip()

# ---------------- DISPLAY FUNCTIONS ----------------
def display_papers(papers, count=20, sort_by="citations", show_full_abstract=False):
    """Display papers sorted by specified criteria."""
    if sort_by == "citations":
        sorted_papers = sorted(papers, key=lambda x: (x.get('citations', 0), x.get('year', 0)), reverse=True)
        print(f"\n🔑 Top {count} Papers by Citations:")
    elif sort_by == "year":
        sorted_papers = sorted(papers, key=lambda x: (x.get('year', 0), x.get('citations', 0)), reverse=True)
        print(f"\n📅 Top {count} Most Recent Papers:")
    else:
        sorted_papers = papers
        print(f"\n📄 Papers (first {count}):")
    
    for idx, p in enumerate(sorted_papers[:count], 1):
        citations = p.get("citations", "N/A")
        year = p.get("year", "N/A")
        venue = p.get("venue", "Unknown")
        abstract_indicator = "📝" if p.get("abstract") else "📄"
        
        print(f"\n{idx}. [{year}] {p['title']}")
        print(f"   {abstract_indicator} Venue: {venue} | Citations: {citations} | Source: {p.get('source', 'N/A')}")
        
        # Show full abstract if available
        if p.get("abstract"):
            if show_full_abstract:
                print(f"   Abstract: {p['abstract']}")
            else:
                abstract_preview = p['abstract'][:200] + "..." if len(p['abstract']) > 200 else p['abstract']
                print(f"   Abstract: {abstract_preview}")

def get_valid_choice(prompt, max_val):
    """Get valid integer choice from user with error handling."""
    while True:
        try:
            choice = input(prompt).strip()
            if not choice:
                print("❌ Please enter a number.")
                continue
            choice_num = int(choice)
            if 1 <= choice_num <= max_val:
                return choice_num
            else:
                print(f"❌ Please enter a number between 1 and {max_val}.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")

# ---------------- MAIN ----------------
def main():
    print("Device set to use cpu")
    author_input = input("Enter author name: ").strip()
    
    if not author_input:
        print("❌ No input provided. Exiting.")
        return

    author_name = None
    affiliations = []
    openalex_papers = []
    ss_papers = []

    print("\n📋 DEBUG: Searching for author by name")
    ss_authors = fetch_semantic_scholar_author(author_input)
    if not ss_authors:
        print("❌ No authors found by name in Semantic Scholar.")
        return
        
    if len(ss_authors) > 1:
        print("\nMultiple authors found. Select one:")
        for idx, a in enumerate(ss_authors, start=1):
            name = a.get("name", "Unknown")
            aff_list = a.get("affiliations", [])
            aff = ", ".join(aff_list) if aff_list else "Unknown"
            paper_count = a.get("paperCount", "N/A")
            print(f"{idx}. {name} | Affiliation: {aff} | Papers: {paper_count}")
        
        choice = get_valid_choice("Enter choice number: ", len(ss_authors))
        author = ss_authors[choice-1]
    else:
        author = ss_authors[0]

    author_id = author.get("authorId")
    author_name = author.get("name", "Unknown")
    affiliations = author.get("affiliations", [])
    
    print(f"\n📋 DEBUG: Selected author: {author_name}")
    print(f"📋 DEBUG: Author ID: {author_id}")
    print(f"📋 DEBUG: Affiliations from SS: {affiliations}")
    
    ss_papers = fetch_semantic_scholar_papers(author_id)
    
    # Search OpenAlex
    openalex_authors = search_openalex_authors_by_name(author_input)
    if openalex_authors:
        numeric_id = openalex_authors[0].get("id", "").split("/")[-1]
        print(f"📋 DEBUG: Using OpenAlex ID: {numeric_id}")
        
        # Get affiliation from OpenAlex if SS doesn't have it
        if not affiliations:
            openalex_institutions = openalex_authors[0].get("last_known_institutions", [])
            if openalex_institutions and isinstance(openalex_institutions, list):
                affiliations = [inst.get("display_name", "") for inst in openalex_institutions if isinstance(inst, dict)]
                print(f"📋 DEBUG: Got affiliations from OpenAlex: {affiliations}")
        
        openalex_papers = fetch_openalex_papers(numeric_id)
    else:
        print("⚠️  DEBUG: No OpenAlex authors found by name")

    # Merge papers with fuzzy deduplication
    papers = merge_papers(openalex_papers, ss_papers)
    
    if not papers:
        print("\n❌ No papers found for this author.")
        return
    
    # Generate summary
    summary = generate_author_summary(author_name, papers, affiliations)

    # Display results
    print("\n" + "="*70)
    print(f"AUTHOR PROFILE: {author_name}")
    print("="*70)
    print(f"Affiliations: {', '.join(affiliations) if affiliations else 'Unknown'}")
    print(f"\n{summary}\n")
    
    # Ask about abstract display preference
    show_full = input("Show full abstracts? (y/n, default: n): ").strip().lower()
    show_full_abstract = (show_full == 'y')
    
    # Display papers sorted by citations
    display_papers(papers, count=20, sort_by="citations", show_full_abstract=show_full_abstract)
    
    # Ask if user wants to see by year
    show_by_year = input("\nShow papers sorted by year instead? (y/n): ").strip().lower()
    if show_by_year == 'y':
        display_papers(papers, count=20, sort_by="year", show_full_abstract=show_full_abstract)
    
    # Export option
    export = input("\nExport results to JSON file? (y/n): ").strip().lower()
    if export == 'y':
        filename = f"{author_name.replace(' ', '_')}_papers.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "author": author_name,
                    "affiliations": affiliations,
                    "summary": summary,
                    "papers": papers
                }, f, indent=2, ensure_ascii=False)
            print(f"✓ Exported to {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")

if __name__ == "__main__":
    main()
