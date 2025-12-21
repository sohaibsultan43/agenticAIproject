"""
ScholarSync - Gap Finder Agent (OpenAI GPT-5 mini)
===================================================
Agent specialized in identifying research gaps and future directions.
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

GAP_FINDER_PROMPT = """You are a research gap identification expert. Analyze papers to find unexplored areas, limitations, and future research directions.

OUTPUT FORMAT (use this exact structure):

## Research Gaps Analysis

### Identified Gaps

#### 1. [Gap Category Name]
• **Description:** [What's missing or unexplored]
• **Why it matters:** [Significance of this gap]
• **Mentioned in:** [Which paper(s) noted this]

#### 2. [Gap Category Name]
• **Description:** [What's missing or unexplored]
• **Why it matters:** [Significance of this gap]
• **Mentioned in:** [Which paper(s) noted this]

#### 3. [Gap Category Name]
• **Description:** [What's missing or unexplored]
• **Why it matters:** [Significance of this gap]
• **Mentioned in:** [Which paper(s) noted this]

### Limitations Across Papers
• [Common limitation 1]
• [Common limitation 2]
• [Common limitation 3]

### Future Research Directions

**High Priority:**
1. [Direction 1] - [Why important]
2. [Direction 2] - [Why important]

**Medium Priority:**
1. [Direction 1] - [Why important]
2. [Direction 2] - [Why important]

### Unexplored Combinations
• [Potential combination of techniques/domains]
• [Another unexplored combination]

---
*Sources: [filenames]*

RULES:
- Focus on ACTIONABLE gaps (not just "more research needed")
- Prioritize gaps by potential impact
- Look for patterns across multiple papers
- Be specific about what's missing
- Suggest concrete research directions"""


class GapFinderAgent(BaseAgent):
    """Agent for identifying research gaps and future directions."""
    
    name = "GapFinderAgent"
    description = "Identifies research gaps, limitations, and future research directions from papers"
    agent_type = AgentType.GAP_FINDER
    
    trigger_keywords = [
        "gap",
        "gaps",
        "limitation",
        "limitations",
        "future work",
        "future research",
        "unexplored",
        "missing",
        "what's missing",
        "research direction",
        "open problem",
        "challenge"
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
        """Identify research gaps and future directions."""
        self.logger.info("Gap finder executing | tenant=%s", context.tenant_id)
        
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
                    {"role": "system", "content": GAP_FINDER_PROMPT},
                    {"role": "user", "content": f"""Based on the following paper content, identify research gaps and future directions.

Paper Content:
{paper_context}

User Query: {query}

Analyze the gaps following the output format. Look for:
1. Explicitly stated limitations
2. Unexplored areas mentioned in future work
3. Implicit gaps (techniques not tried, domains not explored)
4. Patterns across multiple papers"""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("Gap analysis completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query},
                success=True
            )
            
        except Exception as e:
            self.logger.error("Gap analysis failed: %s", str(e))
            return AgentResponse(
                content=f"Error analyzing gaps: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton and register
gap_finder_agent = GapFinderAgent()
AgentRegistry.register(gap_finder_agent)
