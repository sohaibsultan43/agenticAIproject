"""
ScholarSync - Fetcher Module
=============================
This module handles searching ArXiv and downloading research papers.

Phase 2: The Fetcher (Autonomous Agent)
- Searches ArXiv API with refined queries
- Downloads PDFs to local storage
- Sanitizes filenames for safe storage
"""

import os
import re
import arxiv
import requests
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date
from dataclasses import dataclass
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Load environment variables
load_dotenv()

# Configuration
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloaded_papers"))
MAX_PAPERS = int(os.getenv("MAX_PAPERS_PER_SEARCH", 10))

logger = logging.getLogger("ScholarSync.fetcher")
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


@dataclass
class PaperInfo:
    """Data class to store paper metadata."""
    title: str
    authors: List[str]
    abstract: str
    arxiv_id: str
    pdf_url: str
    published: str
    categories: List[str]
    local_path: Optional[str] = None
    source: Optional[str] = None  # Which source: arxiv, semantic_scholar, core, pubmed


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    Convert a paper title into a safe filename.
    
    Args:
        title: The original paper title
        max_length: Maximum length for the filename
        
    Returns:
        A sanitized filename string
    """
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'[^\w\-_.]', '', sanitized)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Remove trailing underscores and add extension
    sanitized = sanitized.rstrip('_')
    
    return f"{sanitized}.pdf"


def _parse_iso_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return date.fromisoformat(d.strip())
    except Exception:
        return None


def search_arxiv(
    query: str,
    max_results: int = MAX_PAPERS,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_scan: int = 200,
) -> List[PaperInfo]:
    """
    Search ArXiv for papers matching the query.
    
    Args:
        query: The search query string
        max_results: Maximum number of papers to retrieve
        
    Returns:
        List of PaperInfo objects
    """
    logger.info("ArXiv search | query=%r", query)
    
    # Clean query: remove markdown formatting that breaks ArXiv API
    clean_query = query.strip()
    # Remove markdown bold/italic markers
    clean_query = clean_query.replace('**', '').replace('*', '')
    # Remove backticks
    clean_query = clean_query.replace('`', '')
    # Remove extra whitespace
    clean_query = ' '.join(clean_query.split())
    
    # Configure the ArXiv search
    # NOTE: We intentionally fetch more than requested and then filter locally.
    # This avoids relying on ArXiv query syntax for date/author and keeps behavior predictable.
    scan_limit = min(max(max_results * 5, max_results), max_scan)
    search = arxiv.Search(
        query=clean_query,  # Use cleaned query
        max_results=scan_limit,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending
    )
    
    papers = []
    client = arxiv.Client()
    
    author_norm = (author or "").strip().lower()
    start_d = _parse_iso_date(start_date)
    end_d = _parse_iso_date(end_date)

    for result in client.results(search):
        published_dt = result.published  # datetime
        published_str = published_dt.strftime("%Y-%m-%d")

        # --- Local filters ---
        if author_norm:
            result_authors = [a.name for a in result.authors]
            if not any(author_norm in a.lower() for a in result_authors):
                continue

        if start_d or end_d:
            pub_date = published_dt.date() if isinstance(published_dt, datetime) else None
            if pub_date is None:
                continue
            if start_d and pub_date < start_d:
                continue
            if end_d and pub_date > end_d:
                continue

        paper = PaperInfo(
            title=result.title,
            authors=[author.name for author in result.authors],
            abstract=result.summary,
            arxiv_id=result.entry_id.split('/')[-1],
            pdf_url=result.pdf_url,
            published=published_str,
            categories=result.categories
        )
        papers.append(paper)
        logger.debug("ArXiv result: %s", paper.title[:80])

        # Stop early once we have the requested amount after filtering
        if len(papers) >= max_results:
            break
    
    logger.info("ArXiv search done | results=%d", len(papers))
    return papers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def search_semantic_scholar(
    query: str,
    max_results: int = 20,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[PaperInfo]:
    """
    Search Semantic Scholar for papers matching the query.

    Notes:
    - We only return papers with an open-access PDF URL (so download works).
    - Filters are applied locally for predictability.
    """
    author_norm = (author or "").strip().lower()
    start_d = _parse_iso_date(start_date)
    end_d = _parse_iso_date(end_date)
    start_year = start_d.year if start_d else None
    end_year = end_d.year if end_d else None

    # Fetch more than needed; many results won't have openAccessPdf
    fetch_limit = min(max(max_results * 4, max_results), 100)
    params = {
        "query": query,
        "limit": fetch_limit,
        "fields": "title,authors,year,abstract,openAccessPdf,url",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "ScholarSync/1.0",
    }

    try:
        resp = requests.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            raise RuntimeError("Semantic Scholar rate limited (429). Please wait ~30-60s and try again.")
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception as e:
        raise RuntimeError(f"Semantic Scholar search failed: {e}") from e

    results = []
    for item in (data.get("data") or []):
        title = (item.get("title") or "").strip()
        if not title:
            continue

        authors_list = [a.get("name", "").strip() for a in (item.get("authors") or [])]
        authors_list = [a for a in authors_list if a]
        if author_norm and not any(author_norm in a.lower() for a in authors_list):
            continue

        year = item.get("year")
        if isinstance(year, int):
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue
            published = str(year)
        else:
            published = ""

        abstract = (item.get("abstract") or "").strip()

        oa = item.get("openAccessPdf") or {}
        pdf_url = (oa.get("url") or "").strip()
        if not pdf_url:
            # Skip papers without a PDF we can download
            continue

        # Prefer stable ID if present; otherwise fall back to Semantic Scholar URL
        paper_id = (item.get("paperId") or item.get("url") or title)[:200]

        results.append(
            PaperInfo(
                title=title,
                authors=authors_list,
                abstract=abstract,
                arxiv_id=paper_id,
                pdf_url=pdf_url,
                published=published,
                categories=[],
            )
        )
        if len(results) >= max_results:
            break

    logger.info("Semantic Scholar results: %s (query=%r)", len(results), query)
    return results


def search_core(
    query: str,
    max_results: int = MAX_PAPERS,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[PaperInfo]:
    """
    Search CORE for open access papers.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        author: Optional author filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    
    Returns:
        List of PaperInfo objects
    """
    logger.info("CORE search | query=%r", query)
    
    # CORE API endpoint
    CORE_API_URL = "https://api.core.ac.uk/v3/search/works"
    api_key = os.getenv("CORE_API_KEY")
    
    if not api_key:
        logger.warning("CORE_API_KEY not set, skipping CORE search")
        return []
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {
            "q": query,
            "limit": max_results,
            "scroll": "false"
        }
        
        response = requests.get(CORE_API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error("CORE search failed: %s", e)
        return []
    
    results = []
    author_norm = (author or "").strip().lower()
    start_d = _parse_iso_date(start_date)
    end_d = _parse_iso_date(end_date)
    
    for item in (data.get("results") or []):
        title = (item.get("title") or "").strip()
        if not title:
            continue
        
        # Author filter
        authors_list = item.get("authors") or []
        if isinstance(authors_list, list):
            authors_list = [str(a) for a in authors_list if a]
        else:
            authors_list = []
        
        if author_norm and not any(author_norm in a.lower() for a in authors_list):
            continue
        
        # Date filter
        published_date = item.get("publishedDate") or item.get("yearPublished")
        if published_date:
            pub_d = _parse_iso_date(str(published_date))
            if pub_d:
                if start_d and pub_d < start_d:
                    continue
                if end_d and pub_d > end_d:
                    continue
                published = str(published_date)
            else:
                published = str(published_date)
        else:
            published = ""
        
        # Get PDF URL
        pdf_url = item.get("downloadUrl") or ""
        if not pdf_url:
            continue
        
        abstract = (item.get("abstract") or "").strip()
        paper_id = item.get("id") or title[:200]
        
        results.append(
            PaperInfo(
                title=title,
                authors=authors_list,
                abstract=abstract,
                arxiv_id=f"core_{paper_id}",
                pdf_url=pdf_url,
                published=published,
                categories=[],
            )
        )
    
    logger.info("CORE results: %s (query=%r)", len(results), query)
    return results


def search_pubmed(
    query: str,
    max_results: int = MAX_PAPERS,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[PaperInfo]:
    """
    Search PubMed and retrieve PDFs from PMC Open Access subset.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        author: Optional author filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    
    Returns:
        List of PaperInfo objects with PMC PDFs
    """
    logger.info("PubMed search | query=%r", query)
    
    # PubMed E-utilities base URL
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    PMC_PDF_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles"
    
    try:
        # Step 1: Search PubMed
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results * 3,  # Get more to filter for PMC
            "retmode": "json"
        }
        
        if author:
            search_params["term"] += f" AND {author}[Author]"
        if start_date and end_date:
            search_params["term"] += f" AND {start_date}:{end_date}[PDAT]"
        
        response = requests.get(ESEARCH_URL, params=search_params, timeout=30)
        response.raise_for_status()
        search_data = response.json()
        
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            logger.info("No PubMed results found")
            return []
        
        # Step 2: Get summaries to find PMC IDs
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        response = requests.get(ESUMMARY_URL, params=summary_params, timeout=30)
        response.raise_for_status()
        summary_data = response.json()
        
        results = []
        for pmid in pmids:
            article = summary_data.get("result", {}).get(pmid, {})
            if not article:
                continue
            
            # Check if article has PMC ID (open access)
            pmc_id = None
            for article_id in article.get("articleids", []):
                if article_id.get("idtype") == "pmc":
                    pmc_id = article_id.get("value")
                    break
            
            if not pmc_id:
                continue  # Skip non-open-access articles
            
            title = article.get("title", "").strip()
            authors = [a.get("name", "") for a in article.get("authors", [])]
            
            # Construct PMC PDF URL
            pdf_url = f"{PMC_PDF_BASE}/{pmc_id}/pdf"
            
            published = article.get("pubdate", "")
            
            results.append(
                PaperInfo(
                    title=title,
                    authors=authors,
                    abstract="",  # PubMed summaries don't include full abstract
                    arxiv_id=f"pmc_{pmc_id}",
                    pdf_url=pdf_url,
                    published=published,
                    categories=["biomedical"],
                )
            )
            
            if len(results) >= max_results:
                break
        
        logger.info("PubMed/PMC results: %s (query=%r)", len(results), query)
        return results
        
    except Exception as e:
        logger.error("PubMed search failed: %s", e)
        return []


def _calculate_relevance_score(paper: PaperInfo, query: str, source: str) -> float:
    """
    Calculate relevance score for ranking papers.
    
    Scoring factors:
    - Title match (40%)
    - Abstract match (30%)
    - Source priority (20%)
    - Recency (10%)
    """
    score = 0.0
    query_lower = query.lower()
    query_terms = set(query_lower.split())
    
    # Title match (40 points)
    title_lower = paper.title.lower()
    title_terms = set(title_lower.split())
    title_overlap = len(query_terms & title_terms) / max(len(query_terms), 1)
    score += title_overlap * 40
    
    # Exact phrase match bonus
    if query_lower in title_lower:
        score += 20
    
    # Abstract match (30 points)
    if paper.abstract:
        abstract_lower = paper.abstract.lower()
        abstract_terms = set(abstract_lower.split())
        abstract_overlap = len(query_terms & abstract_terms) / max(len(query_terms), 1)
        score += abstract_overlap * 30
    
    # Source priority (20 points)
    source_scores = {
        "semantic_scholar": 20,  # Best for recent + comprehensive
        "arxiv": 18,             # Good for CS/physics
        "core": 15,              # Good for open access
        "pubmed": 15             # Good for biomedical
    }
    score += source_scores.get(source, 10)
    
    # Recency (10 points) - prefer papers from last 5 years
    try:
        if paper.published:
            year_str = paper.published.split("-")[0]
            year = int(year_str)
            current_year = 2025
            age = current_year - year
            if age <= 5:
                score += 10 * (1 - age / 5)
    except:
        pass
    
    return score


def _deduplicate_papers(papers: List[tuple]) -> List[PaperInfo]:
    """
    Deduplicate papers based on title similarity.
    
    Args:
        papers: List of (PaperInfo, source, score) tuples
    
    Returns:
        Deduplicated list of PaperInfo objects
    """
    seen_titles = set()
    unique_papers = []
    
    for paper, source, score in papers:
        # Normalize title for comparison
        title_norm = paper.title.lower().strip()
        title_norm = " ".join(title_norm.split())  # Normalize whitespace
        
        # Check for exact match
        if title_norm in seen_titles:
            continue
        
        # Check for very similar titles (fuzzy match)
        is_duplicate = False
        for seen in seen_titles:
            # Simple similarity: if 80% of words match, consider duplicate
            title_words = set(title_norm.split())
            seen_words = set(seen.split())
            if len(title_words) > 0 and len(seen_words) > 0:
                overlap = len(title_words & seen_words)
                similarity = overlap / max(len(title_words), len(seen_words))
                if similarity > 0.9:  # 90% similarity threshold
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_titles.add(title_norm)
            unique_papers.append(paper)
    
    return unique_papers


def unified_search(
    query: str,
    max_results: int = MAX_PAPERS,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sources: Optional[List[str]] = None,
) -> List[PaperInfo]:
    """
    Search across multiple sources and return ranked, deduplicated results.
    
    Args:
        query: Search query
        max_results: Maximum results to return
        author: Optional author filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        sources: List of sources to search (default: all)
                 Options: ["arxiv", "semantic_scholar", "core", "pubmed"]
    
    Returns:
        Ranked and deduplicated list of PaperInfo objects
    """
    logger.info("Unified search | query=%r sources=%s", query, sources)
    
    # Default to all sources
    if sources is None:
        sources = ["semantic_scholar", "arxiv", "core", "pubmed"]
    
    all_papers = []
    
    # Search each source
    for source in sources:
        try:
            if source == "arxiv":
                papers = search_arxiv(query, max_results, author, start_date, end_date)
                for paper in papers:
                    paper.source = "arxiv"  # Set source
                    score = _calculate_relevance_score(paper, query, "arxiv")
                    all_papers.append((paper, "arxiv", score))
            
            elif source == "semantic_scholar":
                papers = search_semantic_scholar(query, max_results, author, start_date, end_date)
                for paper in papers:
                    paper.source = "semantic_scholar"  # Set source
                    score = _calculate_relevance_score(paper, query, "semantic_scholar")
                    all_papers.append((paper, "semantic_scholar", score))
            
            elif source == "core":
                papers = search_core(query, max_results, author, start_date, end_date)
                for paper in papers:
                    paper.source = "core"  # Set source
                    score = _calculate_relevance_score(paper, query, "core")
                    all_papers.append((paper, "core", score))
            
            elif source == "pubmed":
                papers = search_pubmed(query, max_results, author, start_date, end_date)
                for paper in papers:
                    paper.source = "pubmed"  # Set source
                    score = _calculate_relevance_score(paper, query, "pubmed")
                    all_papers.append((paper, "pubmed", score))
        
        except Exception as e:
            logger.error("Search failed for source %s: %s", source, e)
            continue
    
    # Sort by relevance score (descending)
    all_papers.sort(key=lambda x: x[2], reverse=True)
    
    # Deduplicate
    unique_papers = _deduplicate_papers(all_papers)
    
    # Return ALL unique papers (no limit)
    # This means if you request max_results=20 from each of 4 sources,
    # you could get up to 80 papers (minus duplicates)
    results = unique_papers
    
    logger.info("Unified search results: %d unique papers from %d sources (before dedup: %d)", 
                len(results), len(sources), len(all_papers))
    
    return results


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_pdf(paper: PaperInfo, download_dir: Path = DOWNLOAD_DIR) -> Optional[str]:
    """
    Download a PDF from ArXiv with retry logic.
    
    Args:
        paper: PaperInfo object containing paper details
        download_dir: Directory to save the PDF
        
    Returns:
        Path to the downloaded file, or None if failed
    """
    # Ensure download directory exists
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Create safe filename
    filename = sanitize_filename(paper.title)
    filepath = download_dir / filename
    
    # Skip if already downloaded
    if filepath.exists():
        logger.info("Download skipped (exists) | file=%s", filename)
        paper.local_path = str(filepath)
        return str(filepath)
    
    logger.info("Downloading | file=%s", filename)
    
    try:
        # Download the PDF
        response = requests.get(paper.pdf_url, timeout=60)
        response.raise_for_status()
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        paper.local_path = str(filepath)
        logger.info("Downloaded | file=%s", filename)
        return str(filepath)
        
    except requests.RequestException as e:
        logger.warning("Download failed | title=%r error=%s", paper.title, str(e))
        return None


def fetch_papers(query: str, max_results: int = MAX_PAPERS) -> List[PaperInfo]:
    """
    Main function to search and download papers from ArXiv.
    
    Args:
        query: The search query string
        max_results: Maximum number of papers to download
        
    Returns:
        List of PaperInfo objects with local_path populated for downloaded files
    """
    # Search for papers
    papers = search_arxiv(query, max_results)
    
    if not papers:
        print("❌ No papers found for the query")
        return []
    
    # Download each paper
    print(f"\n📥 Downloading {len(papers)} papers...")
    successful_downloads = 0
    
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {paper.title[:50]}...")
        if download_pdf(paper):
            successful_downloads += 1
    
    print(f"\n🎉 Successfully downloaded {successful_downloads}/{len(papers)} papers")
    print(f"📁 Papers saved to: {DOWNLOAD_DIR.absolute()}")
    
    return papers


def get_downloaded_papers() -> List[Path]:
    """
    Get a list of all downloaded PDF files (including subfolders).
    
    Returns:
        List of Path objects for each PDF
    """
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Use recursive glob to find PDFs in subfolders too
    return list(DOWNLOAD_DIR.glob("**/*.pdf"))


# CLI Interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default test query
        query = "Quantum Computing"
    
    print("=" * 60)
    print("ScholarSync - Paper Fetcher")
    print("=" * 60)
    
    papers = fetch_papers(query, max_results=3)
    
    print("\n" + "=" * 60)
    print("Downloaded Papers Summary:")
    print("=" * 60)
    
    for paper in papers:
        if paper.local_path:
            print(f"\n📄 {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:3])}")
            print(f"   Published: {paper.published}")
            print(f"   File: {paper.local_path}")
