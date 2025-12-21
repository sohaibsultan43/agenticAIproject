import os
os.environ['CORE_API_KEY'] = 'pvJ3MjDf9HCgYS4luTaNtbnQ072BsGK8'

from fetcher import search_arxiv

# Test with the problematic query
query = "** `diffusion language model generation NLP`"

print(f"Testing ArXiv with formatted query: {query}")
print()

try:
    papers = search_arxiv(query, max_results=5)
    print(f"[OK] ArXiv returned {len(papers)} papers")
    if papers:
        print(f"First paper: {papers[0].title[:60]}...")
except Exception as e:
    print(f"[FAIL] ArXiv failed: {e}")
