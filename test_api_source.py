import requests
import json

# Test the API endpoint
url = "http://localhost:8000/api/search"
payload = {
    "query": "neural networks",
    "max_results": 3,
    "sources": ["arxiv", "semantic_scholar"]
}

print("Testing API endpoint...")
response = requests.post(url, json=payload)

if response.status_code == 200:
    papers = response.json()
    print(f"\nAPI returned {len(papers)} papers:\n")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.get('title', 'N/A')[:50]}...")
        print(f"   Source: {paper.get('source', 'MISSING!')}")
        print(f"   Has source field: {'source' in paper}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
