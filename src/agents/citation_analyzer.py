"""
ScholarSync - Citation Analyzer Agent (OpenAI GPT-5 mini)
==========================================================
Agent specialized in analyzing citation networks and references.
"""

import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from .base import (
    BaseAgent,
    AgentContext,
    AgentResponse,
    AgentType,
    AgentRegistry
)

load_dotenv()

CITATION_PROMPT = """You are a citation analysis expert. Analyze and extract citation information from research papers.

OUTPUT FORMAT (use this exact structure):

## Citation Analysis: [Paper Title]

### Key References
List the most important references cited:
• **[Author Year]:** [Paper title] - [Why it's significant to this work]
• **[Author Year]:** [Paper title] - [Why it's significant to this work]

### Citation Context
Analyze how citations are used:
• **Supporting:** [List papers that support the main claims]
• **Contrasting:** [List papers that present alternative approaches]
• **Foundational:** [Seminal works this paper builds upon]

### Citation Statistics
• **Total References:** [Number if mentioned]
• **Most Cited Authors:** [Top authors referenced]
• **Citation Patterns:** [Observations about citation behavior]

### Recommended Related Work
Based on the citations, related papers to explore:
1. [Paper/Author suggestion]
2. [Paper/Author suggestion]

---
*Source: [filename]*

RULES:
- Extract ONLY citations explicitly mentioned in the paper
- Note the context in which papers are cited (supporting vs contrasting)
- Identify the most influential references
- Be specific about why each citation matters"""


class CitationAnalyzerAgent(BaseAgent):
    """Agent for analyzing citations and references."""
    
    name = "CitationAnalyzerAgent"
    description = "Analyzes citation networks, key references, and citation context in papers"
    agent_type = AgentType.CITATION_ANALYZER
    
    trigger_keywords = [
        "citation",
        "citations",
        "reference",
        "references",
        "cited",
        "cite",
        "cites",
        "bibliography",
        "related work",
        "prior work",
        "what papers"
    ]
    
    def __init__(self):
        super().__init__()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
    
    async def run(self, query: str, context: AgentContext) -> AgentResponse:
        """Analyze citations in papers."""
        self.logger.info("Citation analyzer executing | tenant=%s", context.tenant_id)
        
        if not self.client:
            return AgentResponse(
                content="Error: OpenAI API key not configured.",
                agent_type=self.agent_type,
                success=False,
                error="OPENAI_API_KEY not set"
            )
        
        paper_context = context.metadata.get("paper_context", "")
        sources = context.metadata.get("sources", [])
        
        if not paper_context:
            return AgentResponse(
                content="No paper content available. Please ingest papers first.",
                agent_type=self.agent_type,
                success=False,
                error="No paper context"
            )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": CITATION_PROMPT},
                    {"role": "user", "content": f"""Analyze the citations in the following paper content.

Paper Content:
{paper_context}

User Query: {query}

Provide a citation analysis following the output format."""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("Citation analysis completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query},
                success=True
            )
            
        except Exception as e:
            self.logger.error("Citation analysis failed: %s", str(e))
            return AgentResponse(
                content=f"Error analyzing citations: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton and register
citation_analyzer_agent = CitationAnalyzerAgent()
AgentRegistry.register(citation_analyzer_agent)
