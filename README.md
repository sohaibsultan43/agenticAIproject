# 🎓 ScholarSync (Multi-Agent Edition)

An autonomous AI research assistant powered by OpenAI GPT-5 mini. ScholarSync uses 6 specialized agents to help you search academic repositories (ArXiv), download papers, build a knowledge base in Weaviate Cloud, and intelligently analyze research.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![OpenAI](https://img.shields.io/badge/LLM-GPT--5%20mini-green.svg)
![Weaviate Cloud](https://img.shields.io/badge/Weaviate-Cloud-purple.svg)

## ✨ Features

- **🔍 Idea Refinement** - AI-powered consultation to convert vague ideas into precise search queries
- **📥 Autonomous Fetching** - Automatically searches ArXiv and downloads relevant papers
- **🧠 Smart Indexing** - Creates embeddings using Gemini and stores them in Weaviate Cloud
- **🤖 6 Specialized Agents** - Intelligent routing to expert agents for different tasks
- **💬 RAG-based Q&A** - Ask questions about your papers with cited answers
- **☁️ Cloud-Powered** - Uses Weaviate Cloud for reliable, scalable vector storage

## 🤖 Specialized Agents

| Agent | Purpose | Example Query |
|-------|---------|---------------|
| **Summarizer** | Generate structured paper summaries | "summarize this paper" |
| **Methodology Extractor** | Extract research methods | "what methodology was used?" |
| **Comparator** | Compare multiple papers | "compare these papers" |
| **Gap Finder** | Identify research gaps | "what are the limitations?" |
| **Citation Analyzer** | Analyze citations | "what papers does this cite?" |
| **General Q&A** | Answer any question (fallback) | Any other question |

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **LLM** | OpenAI GPT-5 mini |
| **Embeddings** | Gemini text-embedding-004 |
| **Orchestration** | LlamaIndex |
| **Vector Database** | Weaviate Cloud |
| **UI** | React + Vite |
| **Data Source** | ArXiv API |

## 📁 Project Structure

```
ScholarSync/
├── downloaded_papers/       # Stores downloaded PDF files
├── .env                     # Your API keys (create from .env.example)
├── .env.example             # Template for environment variables
├── requirements.txt         # Python dependencies
├── fetcher.py               # ArXiv search & download module
├── ingest.py                # PDF embedding & indexing module
├── api.py                   # FastAPI backend
└── frontend/                # React + Vite UI
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **OpenAI API Key** - [Get your key here](https://platform.openai.com/api-keys)
- **Weaviate Cloud Account** - [Sign up free here](https://console.weaviate.cloud/)

### Step 1: Clone & Setup Environment

```powershell
# Navigate to the project
cd ScholarSync

# Create a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Set Up Weaviate Cloud

1. Go to [Weaviate Cloud Console](https://console.weaviate.cloud/)
2. Sign up for a free account
3. Click **Create Cluster** → Choose **Free Sandbox**
4. Wait for the cluster to be ready (1-2 minutes)
5. Copy the **Cluster URL** (e.g., `https://your-cluster-xxxxx.weaviate.network`)
6. Go to **API Keys** → Create a new API key and copy it

### Step 3: Configure API Keys

Edit the `.env` file and add your credentials:

```env
OPENAI_API_KEY=your_openai_api_key_here
WEAVIATE_CLOUD_URL=https://your-cluster-xxxxx.weaviate.network
WEAVIATE_API_KEY=your_weaviate_api_key_here
```

### Step 4: Run ScholarSync

Run the FastAPI backend:

```powershell
uvicorn api:app --host 127.0.0.1 --port 8000 --reload --log-level warning --no-access-log
```

Run the Vite frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:5173 (set `VITE_API_BASE_URL` if your backend is not on `http://localhost:8000/api`)

## 📖 Usage Guide

The React UI calls the FastAPI endpoints to guide you through:

- Idea refinement and query generation with Gemini
- ArXiv search and PDF downloads to `./downloaded_papers`
- PDF ingestion into Weaviate
- RAG-based Q&A over the ingested corpus

### Backend endpoints

- `POST /api/search` — Search ArXiv for papers
- `POST /api/download` — Download PDFs to `./downloaded_papers`
- `POST /api/ingest` — Ingest downloaded PDFs into Weaviate
- `POST /api/chat` — Consultant or Analyst chat (RAG)
- `GET  /api/status` — Service and data health summary

## 🧪 Testing Individual Components

### Test the Fetcher

```powershell
python fetcher.py "Quantum Computing"
```

This will download 3 papers on Quantum Computing.

### Test the Ingestion

```powershell
# First, make sure you have papers downloaded and Weaviate Cloud configured
python ingest.py
```

### Test a Query

```powershell
python ingest.py query "What are the main findings?"
```

## ☁️ Weaviate Cloud Management

Manage your Weaviate Cloud cluster at [console.weaviate.cloud](https://console.weaviate.cloud/):

- **View Data**: Use the Query Console to explore your indexed papers
- **Monitor Usage**: Check storage and query metrics in the dashboard
- **Reset Database**: Delete all collections from the console if needed
- **API Keys**: Manage access keys in the cluster settings

## 🔧 Configuration Options

All configuration is done via the `.env` file:

```env
# Required - Google AI
GOOGLE_API_KEY=your_google_api_key_here

# Required - Weaviate Cloud
WEAVIATE_CLOUD_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your_weaviate_api_key_here

# Optional
DOWNLOAD_DIR=./downloaded_papers
MAX_PAPERS_PER_SEARCH=10
```

## 🐛 Troubleshooting

### "Connection failed" error

1. Check that your Weaviate Cloud cluster is running at [console.weaviate.cloud](https://console.weaviate.cloud/)
2. Verify the `WEAVIATE_CLOUD_URL` is correct (should start with `https://`)
3. Make sure the `WEAVIATE_API_KEY` is valid

### "API key not set" error

1. Open `.env` file
2. Replace placeholder values with your actual API keys:
   - `GOOGLE_API_KEY` from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - `WEAVIATE_CLOUD_URL` and `WEAVIATE_API_KEY` from [Weaviate Cloud](https://console.weaviate.cloud/)
3. Restart the application

### Papers not being found

Try different search queries. ArXiv search works best with:
- Specific technical terms
- Author names
- Paper titles or keywords

### Memory issues with large PDFs

The system chunks PDFs into smaller pieces. If you encounter memory issues:
1. Reduce `Settings.chunk_size` in `ingest.py`
2. Process fewer papers at once

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ScholarSync Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Phase 1    │    │   Phase 2    │    │   Phase 3    │   │
│  │  Consultant  │───▶│   Fetcher    │───▶│   Analyst    │   │
│  │              │    │              │    │              │   │
│  │ Gemini Chat  │    │  ArXiv API   │    │ RAG Query    │   │
│  │ Idea Refine  │    │  Download    │    │ Embeddings   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                             │                    │           │
│                             ▼                    ▼           │
│                    ┌──────────────┐    ┌──────────────┐     │
│                    │    Local     │    │  Weaviate    │     │
│                    │  File Store  │    │    Cloud     │     │
│                    │    (PDFs)    │    │  (Vectors)   │     │
│                    └──────────────┘    └──────────────┘     │
│                                                  ☁️          │
└─────────────────────────────────────────────────────────────┘
```

## 📝 License

MIT License - Feel free to use and modify for your research needs.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) - LLM and Embeddings
- [LlamaIndex](https://www.llamaindex.ai/) - RAG Framework
- [Weaviate](https://weaviate.io/) - Vector Database
- [ArXiv](https://arxiv.org/) - Research Papers
