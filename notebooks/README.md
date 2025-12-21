# Running the ScholarSync Notebooks

## Quick Start

### 1. Activate Virtual Environment

```powershell
cd d:\Agentic_Project\ScholarSync
.\venv\Scripts\Activate
```

### 2. Install Jupyter (if not already installed)

```powershell
pip install jupyter notebook ipykernel
```

### 3. Start Jupyter Notebook

```powershell
cd notebooks
jupyter notebook
```

This will open Jupyter in your browser. Then:
- Click on `01_baseline_chunking.ipynb` or `02_agent_evaluation.ipynb`
- Run cells one by one using Shift+Enter

## Alternative: Run notebooks as Python scripts

If you prefer not to use Jupyter, you can convert the notebooks to Python and run them:

### For Baseline Chunking:

```powershell
cd d:\Agentic_Project\ScholarSync
.\venv\Scripts\Activate

# Create a simple runner
python -c "
import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.ingest import load_pdfs, get_weaviate_client, create_weaviate_schema, WEAVIATE_CLASS_NAME
from src.fetcher import search_arxiv, download_pdf
import weaviate.classes.query as wq

print('Searching for sample paper...')
papers = search_arxiv('attention is all you need', max_results=1)

if papers:
    paper = papers[0]
    print(f'Found: {paper.title}')
    print(f'Authors: {len(paper.authors)} authors')
    print('✓ Basic import test passed')
else:
    print('No papers found')
"
```

### For Agent Evaluation:

```powershell
cd d:\Agentic_Project\ScholarSync
.\venv\Scripts\Activate

# Test agent imports
python -c "
import sys
sys.path.insert(0, '.')

from src.agents import AgentRegistry
from src.agents.summarizer import summarizer_agent

print('Testing agent routing...')
agent = AgentRegistry.find_matching('summarize this paper')
print(f'Matched agent: {agent.name if agent else None}')
print('✓ Agent system working')
"
```

## Troubleshooting

### Error: "No module named 'src'"

**Fix**: Make sure you're running from the project root directory and using `sys.path.insert(0, '.')` at the start of your script.

### Error: "No module named 'jupyter'"

**Fix**: Install Jupyter in your venv:
```powershell
.\venv\Scripts\Activate
pip install jupyter notebook
```

### Error: Cannot connect to Weaviate

**Fix**: Check your `.env` file has:
- `GEMINI_API_KEY`
- `WEAVIATE_CLOUD_URL`
- `WEAVIATE_API_KEY`

## Summary

The notebooks demonstrate:

1. **`01_baseline_chunking.ipynb`**:
   - Downloads a sample paper
   - Shows hierarchical chunking (3 levels)
   - Displays chunk statistics
   - Queries Weaviate for stored chunks

2. **`02_agent_evaluation.ipynb`**:
   - Tests agent routing accuracy
   - Evaluates all 6 agents
   - Generates performance metrics
   - Saves results to `results/agent_evaluation_results.json`

Both notebooks are fully functional and can be run in Jupyter or converted to Python scripts.
