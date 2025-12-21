import os
os.environ['CORE_API_KEY'] = 'pvJ3MjDf9HCgYS4luTaNtbnQ072BsGK8'

from fetcher import unified_search

print("Testing unified search with ALL papers from each source...")
print("Requesting 10 papers from each of 3 sources (arxiv, semantic_scholar, core)")
print()

papers = unified_search("neural networks", max_results=10, sources=["arxiv", "semantic_scholar", "core"])

print(f"Total unique papers returned: {len(papers)}")
print()

# Count by source
sources_count = {}
for paper in papers:
    source = paper.source or "unknown"
    sources_count[source] = sources_count.get(source, 0) + 1

print("Papers by source:")
for source, count in sources_count.items():
    print(f"  {source}: {count}")

print("\nFirst 5 papers:")
for i, paper in enumerate(papers[:5], 1):
    print(f"{i}. [{paper.source}] {paper.title[:50]}...")
