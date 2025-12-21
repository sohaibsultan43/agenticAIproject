# 🎓 ScholarSync - Multi-Agent Research Assistant

> An intelligent research assistant powered by OpenAI GPT-5 mini with 6 specialized agents for autonomous paper discovery, analysis, and knowledge extraction.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![OpenAI](https://img.shields.io/badge/LLM-GPT--5%20mini-green.svg)
![Weaviate](https://img.shields.io/badge/Vector%20DB-Weaviate%20Cloud-purple.svg)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Specialized Agents](#-specialized-agents)
- [Technology Stack](#%EF%B8%8F-technology-stack)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Configuration](#%EF%B8%8F-configuration)
- [Troubleshooting](#-troubleshooting)

---

## 🌟 Overview

ScholarSync is an autonomous AI research assistant that helps researchers:
- **Discover** relevant papers from ArXiv based on vague research ideas
- **Download** and organize papers automatically
- **Index** papers in a cloud vector database for semantic search
- **Analyze** papers using 6 specialized AI agents
- **Extract** insights through intelligent Q&A

The system uses **intelligent agent routing** to automatically select the best agent for each query, ensuring expert-level responses for different types of research questions.

---

## ✨ Key Features

### 🔍 **Two-Phase Workflow**

#### Phase 1: Consultant (Idea → Papers)
- **Idea Refinement**: AI helps convert vague research ideas into precise search queries
- **Autonomous Search**: Searches ArXiv with intelligent query generation
- **Smart Download**: Automatically downloads relevant PDFs
- **Cloud Indexing**: Embeds and stores papers in Weaviate Cloud

#### Phase 2: Analyst (Papers → Insights)
- **Multi-Agent System**: 6 specialized agents for different analysis tasks
- **Intelligent Routing**: Automatically selects the best agent based on your question
- **RAG-Powered**: Retrieval-Augmented Generation for accurate, cited answers
- **Unlimited Output**: No token limits - agents decide response length

### 🎯 **Core Capabilities**

- ✅ **Multi-tenant Support**: Isolated sessions for different research projects
- ✅ **Cloud-Native**: Fully cloud-powered with Weaviate Cloud
- ✅ **Real-time UI**: Modern React interface with live updates
- ✅ **Cited Responses**: All answers include source citations
- ✅ **Agent Badges**: See which agent handled your query
- ✅ **Session Management**: Save and resume research sessions

---

## 🤖 Specialized Agents

ScholarSync uses **keyword-based routing** to automatically select the best agent for your query:

| Agent | Purpose | Trigger Keywords | Example Query |
|-------|---------|------------------|---------------|
| **SummarizerAgent** | Generate structured paper summaries | summarize, summary, tldr, overview, brief | "summarize this paper" |
| **MethodologyExtractorAgent** | Extract research methodologies | methodology, method, approach, technique | "what methodology was used?" |
| **ComparatorAgent** | Compare multiple papers | compare, comparison, difference, versus | "compare these papers" |
| **GapFinderAgent** | Identify research gaps & limitations | gap, limitation, future work, missing | "what are the limitations?" |
| **CitationAnalyzerAgent** | Analyze citations and references | citation, reference, cite, bibliography | "what papers does this cite?" |
| **GeneralQAAgent** | Answer any research question (fallback) | *(any other query)* | "what is the main contribution?" |

### 🎯 How Agent Routing Works

1. **Keyword Matching**: System scores your query against each agent's keywords
2. **Priority Scoring**: Keywords at the start of your query get higher weight
3. **Best Match**: Highest-scoring agent handles your request
4. **Fallback**: If no strong match, GeneralQAAgent handles it

---

## 🛠️ Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | OpenAI GPT-5 mini | All agent responses (auto token limits) |
| **Embeddings** | Gemini text-embedding-004 | Document embeddings for RAG |
| **Vector DB** | Weaviate Cloud | Semantic search & storage |
| **Framework** | FastAPI | REST API backend |
| **Orchestration** | LlamaIndex | RAG pipeline management |
| **PDF Parsing** | LlamaParse (optional) | Enhanced equation/table extraction |

### Frontend
| Component | Technology |
|-----------|------------|
| **Framework** | React 18 |
| **Build Tool** | Vite |
| **Styling** | CSS3 with modern features |
| **Markdown** | ReactMarkdown + GFM |

### Data Sources
- **ArXiv API**: Academic paper search and download
- **Weaviate Cloud**: Free tier with 1GB storage

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Search     │  │   Download   │  │   Chat       │      │
│  │   Papers     │  │   & Ingest   │  │   Interface  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (api.py)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Agent Registry & Router                  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │   │
│  │  │Summary │ │Method  │ │Compare │ │  Gap   │  ...   │   │
│  │  │  Agent │ │ Agent  │ │ Agent  │ │ Agent  │        │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   ArXiv      │  │  LlamaIndex  │  │   OpenAI     │     │
│  │   Fetcher    │  │  RAG Engine  │  │   GPT-5 mini │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Weaviate Cloud (Vector DB)                │
│  • Multi-tenant collections                                  │
│  • Gemini embeddings                                         │
│  • Semantic search                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 16+** (for frontend)
- **Google Gemini API Key** - [Get it here](https://aistudio.google.com/app/apikey)
- **Weaviate Cloud Account** - [Sign up free](https://console.weaviate.cloud/)

### Installation (Step-by-Step)

#### 1. Clone the Repository

```powershell
git clone <your-repo-url>
cd ScholarSync
```

#### 2. Set Up Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate  # Windows PowerShell
# source venv/bin/activate  # Linux/Mac

# Verify Python version
python --version  # Should be 3.10+
```

#### 3. Install Python Dependencies

```powershell
# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list | Select-String "llama-index"
```

#### 4. Configure Environment Variables

Create a `.env` file from the template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required: Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Required: Weaviate Cloud
WEAVIATE_CLOUD_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your_weaviate_api_key_here

# Optional: OpenAI (if using GPT instead of Gemini)
OPENAI_API_KEY=sk-...

# Optional: Enhanced PDF parsing
LLAMA_CLOUD_API_KEY=llx-...

# Optional: Configuration
DOWNLOAD_DIR=./downloaded_papers
HOST=127.0.0.1
PORT=8000
```

**How to get API keys:**

1. **Gemini API Key**: 
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create new API key
   - Copy and paste into `.env`

2. **Weaviate Cloud**:
   - Visit [Weaviate Console](https://console.weaviate.cloud/)
   - Create a free sandbox cluster
   - Copy cluster URL and API key

#### 5. Setup Frontend

```powershell
cd frontend
npm install
cd ..
```

#### 6. Verify Setup

```powershell
# Test Python imports
python -c "from src.api import app; print('✓ Backend imports working')"

# Test frontend dependencies
cd frontend
npm list react
cd ..
```

---

### Running the Application

#### Option 1: Quick Start (Recommended)

**Terminal 1 - Backend:**
```powershell
python run_api.py
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

#### Option 2: Development Mode

**Backend with auto-reload:**
```powershell
uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

**Frontend with hot-reload:**
```powershell
cd frontend
npm run dev -- --host
```

#### Option 3: Docker (if configured)

```powershell
docker-compose up
```

---

### Access Points

Once both services are running:

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

### Demo Commands & Sample Inputs

#### Sample Workflow 1: Research Paper Discovery

1. **Open Frontend**: Navigate to http://localhost:5173

2. **Start Consultant Phase**: Enter a research idea
   ```
   Sample Input: "I want to research transformer models for natural language processing"
   ```

3. **Review Search Plan**: AI generates a structured plan with:
   - Research goal
   - Key concepts
   - Methodologies
   - Search keywords
   - ArXiv search query

4. **Click "Search with this query"**: System searches ArXiv

5. **Select Papers**: Choose 3-5 papers from results

6. **Download & Ingest**: Click "Download Selected" then "Ingest Papers"

7. **Switch to Analyst Phase**: Click "Analyst" tab

8. **Ask Questions**:
   ```
   Sample Queries:
   - "Summarize the main contributions of these papers"
   - "What methodology do they use?"
   - "Compare the different approaches"
   - "What are the limitations?"
   - "What papers do they cite?"
   ```

#### Sample Workflow 2: API Testing (cURL)

**Health Check:**
```bash
curl http://localhost:8000/api/health
```

**Search Papers:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer neural networks",
    "max_results": 5,
    "tenant_id": "demo"
  }'
```

**Chat (Consultant Phase):**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to research attention mechanisms",
    "phase": "consultant",
    "tenant_id": "demo"
  }'
```

**System Status:**
```bash
curl http://localhost:8000/api/status?tenant_id=demo
```

#### Expected Outputs

**1. Consultant Response:**
```markdown
### 🎯 Research Goal
This research aims to explore how attention mechanisms enable neural networks 
to focus on relevant parts of input sequences...

### 💡 Core Concepts
- **Self-Attention**: Mechanism allowing models to weigh importance...
- **Multi-Head Attention**: Parallel attention layers for diverse representations...
...

Search Query: `attention mechanism transformer neural networks`
```

**2. Analyst Response (Summarization):**
```markdown
**Summary**: The paper introduces the Transformer architecture, which relies
entirely on self-attention mechanisms...

**Key Points**:
- Eliminates recurrence and convolutions
- Uses multi-head attention for parallel processing
- Achieves SOTA on WMT translation tasks

[Source: attention_is_all_you_need.pdf, p.3]
```

---

### Running Experiments

#### Baseline Chunking Notebook

```powershell
cd notebooks
python 01_baseline_chunking.py
```

**Expected Output**: Demonstrates how a paper is split into hierarchical chunks with statistics.

#### Agent Evaluation Notebook

```powershell
cd notebooks  
python 02_agent_evaluation.py
```

**Expected Output**: Agent routing accuracy report (should be ~95%) and response quality scores.

---

### Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'src'`
```powershell
# Solution: Use run_api.py instead of direct uvicorn
python run_api.py
```

**Issue**: `Weaviate connection failed`
```powershell
# Verify your .env has correct values
Get-Content .env | Select-String "WEAVIATE"

# Test connection
python -c "from src.ingest import get_weaviate_client; client = get_weaviate_client(); print('✓ Connected'); client.close()"
```

**Issue**: Frontend can't connect to backend
```powershell
# Check backend is running on port 8000
curl http://localhost:8000/api/health

# Verify frontend API URL
cat frontend/src/api.js | Select-String "baseURL"
```

---

---

## 📖 Usage Guide

### Phase 1: Finding Papers (Consultant Mode)

1. **Enter Research Idea**
   ```
   "I want to research diffusion models for text generation"
   ```

2. **AI Refines Query**
   - System generates precise ArXiv search query
   - Shows suggested search terms

3. **Review & Download**
   - Browse search results
   - Select papers to download
   - Click "Download & Process"

4. **Automatic Indexing**
   - Papers are embedded and stored in Weaviate
   - Ready for analysis

### Phase 2: Analyzing Papers (Analyst Mode)

Once papers are ingested, ask questions:

**Summarization:**
```
"Summarize the main paper"
→ SummarizerAgent provides structured summary
```

**Methodology:**
```
"What methodology did they use?"
→ MethodologyExtractorAgent extracts methods
```

**Comparison:**
```
"Compare the approaches in these papers"
→ ComparatorAgent analyzes differences
```

**Gap Analysis:**
```
"What are the limitations?"
→ GapFinderAgent identifies research gaps
```

**Citations:**
```
"What papers does this cite?"
→ CitationAnalyzerAgent analyzes references
```

**General Questions:**
```
"What were the main results?"
→ GeneralQAAgent answers using RAG
```

### Agent Badges

Each response shows which agent handled it:
```
GeneralQAAgent [Agent]
```

---

## 📁 Project Structure

```
ScholarSync/
├── agents/                      # AI Agent System
│   ├── base.py                 # Base agent class & registry
│   ├── summarizer.py           # Paper summarization
│   ├── methodology_extractor.py # Method extraction
│   ├── comparator.py           # Paper comparison
│   ├── gap_finder.py           # Gap analysis
│   ├── citation_analyzer.py    # Citation analysis
│   └── general_qa.py           # General Q&A (fallback)
│
├── frontend/                    # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatPanel.jsx   # Main chat interface
│   │   ├── api.js              # API client
│   │   └── App.jsx             # Root component
│   └── package.json
│
├── downloaded_papers/           # PDF storage
├── api.py                       # FastAPI backend
├── fetcher.py                   # ArXiv search & download
├── ingest.py                    # PDF embedding & indexing
├── logging_utils.py             # Logging configuration
├── requirements.txt             # Python dependencies
├── .env                         # Your API keys (create this)
├── .env.example                 # Template
└── README.md                    # This file
```

---

## 📡 API Documentation

### Endpoints

#### `POST /api/chat`
Chat with the system (both phases)

**Request:**
```json
{
  "message": "summarize this paper",
  "phase": "analyst",
  "history": [],
  "tenant_id": "session-123"
}
```

**Response:**
```json
{
  "response": "## Summary: Paper Title...",
  "sources": ["paper1.pdf", "paper2.pdf"],
  "agent": "SummarizerAgent"
}
```

#### `POST /api/search`
Search ArXiv for papers

#### `POST /api/download`
Download selected papers

#### `POST /api/ingest`
Embed and index papers

#### `GET /api/status`
Get system status and paper count

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for GPT-5 mini |
| `WEAVIATE_CLOUD_URL` | ✅ Yes | Your Weaviate cluster URL |
| `WEAVIATE_API_KEY` | ✅ Yes | Weaviate API key |
| `LLAMA_CLOUD_API_KEY` | ❌ No | For enhanced PDF parsing |
| `DOWNLOAD_DIR` | ❌ No | Paper storage directory (default: `./downloaded_papers`) |
| `MAX_PAPERS_PER_SEARCH` | ❌ No | Max search results (default: 10) |

### Agent Configuration

All agents use **auto token limits** - OpenAI GPT-5 mini decides response length based on content.

To modify agent behavior, edit the prompts in `agents/<agent_name>.py`.

---

## 🔧 Troubleshooting

### Backend Issues

**"ModuleNotFoundError: No module named 'agents.literature_mapper'"**
- Run: `Remove-Item -Recurse -Force agents\__pycache__`
- Restart backend

**"OpenAI API key not configured"**
- Check `.env` file has `OPENAI_API_KEY=sk-...`
- Restart backend

**"Weaviate connection failed"**
- Verify `WEAVIATE_CLOUD_URL` and `WEAVIATE_API_KEY`
- Check cluster is running in Weaviate Cloud Console

### Frontend Issues

**Agent badges not showing**
- Hard refresh browser: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
- Clear browser cache

**"Network Error"**
- Ensure backend is running on `http://localhost:8000`
- Check CORS settings in `api.py`

### Common Issues

**Papers not being indexed**
- Check Weaviate Cloud quota (free tier: 1GB)
- Verify papers downloaded to `downloaded_papers/`
- Check backend logs for errors

**Slow responses**
- OpenAI API rate limits
- Large paper context (try fewer papers)

---

## 🎯 Best Practices

1. **Start Specific**: More specific queries get better agent routing
2. **One Topic**: Focus on one research topic per session
3. **Ingest First**: Download and ingest papers before asking questions
4. **Use Keywords**: Include agent trigger keywords for better routing
5. **Check Sources**: Review cited sources in responses

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions

---

**Built with ❤️ using OpenAI GPT-5 mini, Weaviate Cloud, and React**
