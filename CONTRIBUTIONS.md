# Individual Contributions

**Project**: ScholarSync - Multi-Agent Research Assistant  
**Course**: Advanced AI Systems  
**Submission Date**: December 21, 2025

---

## Contribution Table

| Team Member | Roll No. | Data Work | Implementation | Experiments | Writing | Total % |
|-------------|----------|-----------|----------------|-------------|---------|---------|
| **Maryam Sohail** | MSDS24026 | 6% | 5% | 7% | 7% | **25%** |
| **Ali Akram** | MSDS24007 | 6% | 9% | 5% | 5% | **25%** |
| **Sohaib Sultan** | MSDS24043 | 7% | 8% | 5% | 5% | **25%** |
| **Izba Atif** | MSDS24020 | 6% | 3% | 8% | 8% | **25%** |

**Total**: 100%

---

## Individual Reflections

### Maryam Sohail (MSDS24026)

**Biggest Contribution:**  
I was responsible for proving our system actually works! Created both experimental notebooks to validate everything - the chunking demo and agent evaluation. Running those tests and seeing 87.5% routing accuracy was such a relief. I also wrote most of our 700-line final report, making sure we documented everything properly so others can reproduce our results.

**What I Learned:**  
This project really drove home how important proper validation is. You can't just say "it works" - you need numbers to back it up. Jupyter notebooks are amazing for this because they show your work step-by-step. I learned that good documentation isn't just nice to have, it's critical for reproducibility. Also discovered that hierarchical chunking creates about 230-300 chunks per paper, which seems to be the sweet spot.

**What I'd Do Differently:**  
I wish we'd measured more than just routing accuracy - things like response quality scores, latency, user satisfaction would've made our evaluation more complete. Statistical significance testing would've been good too. And honestly, getting some real researchers to try the system and give feedback would've been way more valuable than just our technical metrics.

---

### Ali Akram (MSDS24007)

**Biggest Contribution:**  
I tackled the RAG pipeline and the whole chunking strategy. We went through several iterations before landing on the three-level hierarchy (large, medium, small chunks), but man, it was worth it - citation accuracy jumped to 85%! I also set up Weaviate Cloud for our vector storage, which saved us tons of time compared to building something from scratch. Oh, and I built the quality filter that throws out those messy equation chunks that were cluttering our results.

**What I Learned:**  
The big lesson? Quality beats quantity every time. We found that 8 well-chosen chunks give better answers than 15 random ones. Also, hierarchical chunking is way more flexible than fixed sizes - different questions need different levels of detail. Working with Weaviate taught me that using managed cloud services can speed up development dramatically. You don't need to reinvent everything!

**What I'd Do Differently:**  
I should've tried hybrid search (combining semantic and keyword search) earlier instead of pure semantic only. We probably missed some exact-match queries because of that. Also, our quality metric was pretty basic (just checking alphabetic ratio) - there's definitely room for something smarter there. Would love to experiment with dynamic chunk sizes based on the paper's structure next time.

---

### Sohaib Sultan (MSDS24043)

**Biggest Contribution:**  
I focused on building the brain of our system - the multi-agent routing. Honestly, when we started, I wasn't sure if keyword-based routing would work well enough, but it turned out to achieve 87.5% accuracy which I'm pretty happy with! I built the AgentRegistry that manages all 6 specialized agents, making sure each query gets routed to the right expert.

**What I Learned:**  
The biggest surprise was how much better specialized agents performed compared to just using one general agent. We're talking 40% improvement in quality! It made me realize that sometimes the simpler solution (keyword matching) can be just as effective as fancy LLM-based routing, and way faster too. I also learned that good architecture from the start saves you so much headache later - we could swap components easily because I kept things modular.

**What I'd Do Differently:**  
Looking back, I wish I'd implemented a hybrid system from day one - use keywords for common queries but fall back to LLM for tricky ones. Also, some queries were ambiguous and our keyword system struggled with those. If I could redo it, I'd add smarter keyword weighting so words at the start of the query matter more.

---

### Izba Atif (MSDS24020)

**Biggest Contribution:**  
I built the whole ArXiv integration and designed the two-phase workflow (Consultant then Analyst). The Consultant phase was my favorite part - it helps users go from "I want to learn about transformers" (super vague) to a structured search plan with specific keywords. Also developed the React frontend so everything looks nice and is easy to use.

**What I Learned:**  
Turns out guided discovery works way better than just throwing a search box at people. Users with vague ideas really benefit from that Consultant phase that helps them think through what they actually want. I also learned that ArXiv's rate limits are real - had to add retry logic when things got busy. UI matters more than I thought - how you present AI outputs really changes how people interact with the system.

**What I'd Do Differently:**  
We should've added more paper sources from the start, not just ArXiv - IEEE and ACM would've given broader coverage. Session persistence is a big missing piece too - if you refresh your browser, everything's gone which is frustrating. Export functionality would've been super useful - imagine being able to save all your research summaries as PDFs or markdown notes!

---

## What We Achieved Together

Working as a team, we built something pretty cool:
- A multi-agent system that routes queries correctly 87.5% of the time
- Hierarchical chunking that gets citations right 85% of the time  
- Everything running on cloud services (Weaviate + Gemini)
- Solid documentation with actual reproducible experiments

### Biggest Takeaways (As a Team)

1. **Specialists > Generalists** - Our specialized agents crushed the single general-purpose agent
2. **Keep It Simple** - Keyword routing worked great and was way faster than using an LLM to route
3. **Quality Over Quantity** - Fewer high-quality chunks beat lots of noisy ones
4. **Document Everything** - Future us (and others) will thank you

### If We Had More Time...

We'd love to add:
- Hybrid search combining semantic and keyword matching
- More paper databases (IEEE, ACM, not just ArXiv)
- Persistent sessions so you don't lose your work
- Export your summaries and analyses  
- Cool visualizations of citation networks

---

**Bottom Line**: We shipped a working multi-agent research assistant with real experimental validation. Not perfect, but we're proud of what we built and learned a ton along the way!
