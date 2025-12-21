"""
ScholarSync - Comparator Agent (OpenAI GPT-5 mini)
===================================================
Agent specialized in comparing multiple research papers.
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

COMPARATOR_PROMPT = """You are a research paper comparison expert. Compare multiple papers and highlight similarities, differences, and relative strengths.

OUTPUT FORMAT (use this exact structure):

## Comparison: [Paper A] vs [Paper B]

### Overview
• **Paper A:** [Brief description]
• **Paper B:** [Brief description]

### Key Similarities
• [Similarity 1]
• [Similarity 2]
• [Similarity 3]

### Key Differences

| Aspect | Paper A | Paper B |
|--------|---------|---------|
| **Approach** | [Approach A] | [Approach B] |
| **Dataset** | [Dataset A] | [Dataset B] |
| **Performance** | [Metrics A] | [Metrics B] |
| **Strengths** | [Strength A] | [Strength B] |
| **Limitations** | [Limitation A] | [Limitation B] |

### Relative Strengths
• **Paper A excels at:** [What A does better]
• **Paper B excels at:** [What B does better]

### Recommendations
• **Use Paper A when:** [Scenario]
• **Use Paper B when:** [Scenario]

---
*Sources: [filenames]*

RULES:
- Be objective and balanced
- Use specific examples from papers
- Highlight both similarities AND differences
- Use tables for side-by-side comparison
- Bold key terms with **term**"""


class ComparatorAgent(BaseAgent):
    """Agent for comparing multiple research papers."""
    
    name = "ComparatorAgent"
    description = "Compares multiple papers side-by-side, highlighting similarities, differences, and relative strengths"
    agent_type = AgentType.COMPARATOR
    
    trigger_keywords = [
        "compare",
        "comparison",
        "vs",
        "versus",
        "difference",
        "differences",
        "similar",
        "contrast",
        "which is better",
        "how do they differ"
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
        """Compare multiple papers."""
        self.logger.info("Comparator agent executing | tenant=%s", context.tenant_id)
        
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
        
        if len(sources) < 2:
            return AgentResponse(
                content="Comparison requires at least 2 papers. Please ingest more papers or ask about specific papers.",
                agent_type=self.agent_type,
                success=False,
                error="Insufficient papers for comparison"
            )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": COMPARATOR_PROMPT},
                    {"role": "user", "content": f"""Based on the following content from multiple papers, provide a detailed comparison.

Paper Content:
{paper_context}

User Query: {query}

Compare the papers following the output format."""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("Comparison completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query, "papers_compared": len(sources)},
                success=True
            )
            
        except Exception as e:
            self.logger.error("Comparison failed: %s", str(e))
            return AgentResponse(
                content=f"Error comparing papers: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton and register
comparator_agent = ComparatorAgent()
AgentRegistry.register(comparator_agent)
