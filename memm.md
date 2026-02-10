# Memory Capabilities in Agentic Frameworks and Standalone Systems

## Executive summary
Agentic frameworks provide short-term (in-session) context handling and vary in support for persistent (cross-session) memory. Dedicated memory systems (Mem0, Letta, Zep, LangMem) focus on persistence, retrieval, and structuring of knowledge; they can be integrated into most frameworks to improve coherence, personalization, and reliability over time.

**Key takeaways**
- **Claude Agent SDK**: minimal long-term memory; relies on developer-managed persistence and careful context management.
- **LangGraph + LangMem**: explicit semantic/episodic/procedural patterns; can also optimize agent instructions.
- **CrewAI**: built-in short-term + long-term + entity memory; can swap in external memory providers.
- **Google ADK**: session state + pluggable MemoryService (e.g., Vertex AI Memory Bank) for persistent recall.

---

## Memory concepts used in agents

### Short-term vs long-term memory
- **Short-term (working) memory**: what the agent can access in the current interaction/execution thread (usually the model context window + current state).
- **Long-term memory**: persisted across sessions and retrieved later (files/DB/vector store/knowledge graph).

### Semantic, episodic, procedural memory
A practical mapping for AI agents:
- **Semantic memory**: stable facts and preferences (user profile, domain facts).
- **Episodic memory**: records of past interactions or events (task runs, conversation highlights, outcomes).
- **Procedural memory**: stored ways of doing things (rules, policies, playbooks), often encoded in prompts and tool-use patterns.

### Self-improvement via memory
Self-improvement can mean:
1) better personalization and fewer repeated mistakes via persistent memory, and/or  
2) evolving procedures (updating instructions based on outcomes).

---

## Framework-by-framework memory capabilities

### Claude Agent SDK (Anthropic)
- **Short-term**: context window + developer summarization/compaction for long tasks.
- **Long-term**: developer-managed persistence (files/logs).
- **Semantic / episodic**: notes and run journals stored as artifacts.
- **Procedural**: mostly prompt-driven; reflective/self-improvement loops are developer-implemented.
- **Self-improvement**: continuity via persisted artifacts and “carry-forward” context.

### LangChain LangGraph + LangMem
- **Short-term**: thread-scoped state + checkpointing.
- **Long-term**: persistent namespaces + stores for memory.
- **Semantic**: structured fact/profile extraction and retrieval.
- **Episodic**: store distilled cases/snippets for reuse (few-shot style guidance).
- **Procedural**: can optimize instructions/policy based on outcomes (procedural self-improvement).
- **Self-improvement**: retention + procedure evolution.

### CrewAI
- **Short-term**: retrieval over recent context (RAG-style).
- **Long-term**: persisted outcomes/insights; entity-focused memory.
- **Semantic / episodic**: entity facts + task results (experiences).
- **Procedural**: prompt/tool-driven; usually static by default.
- **Self-improvement**: accumulates learnings; external memory providers can boost personalization.

### Google Agent Development Kit (ADK)
- **Short-term**: session state (key–value) + event history (SessionService).
- **Long-term**: MemoryService; Vertex AI Memory Bank for distilled recall.
- **Semantic / episodic**: summarized/extracted memories; optional transcript recall depending on implementation.
- **Procedural**: in prompt/code; ADK emphasizes orchestration and state.
- **Self-improvement**: personalization and continuity via long-term memory.

---

## Standalone memory systems and how they fit

### Mem0
- Personalization-focused memory layer that extracts preferences and patterns over time.
- Framework-agnostic; integrates with Claude, LangChain/LangGraph, CrewAI, or custom stacks.
- Improves agent performance by making behavior progressively more consistent and tailored.

### Letta
- Layered memory design: message buffer, pinned core blocks, recall (full logs), archival (processed store).
- Uses summarization/eviction/consolidation to keep memory compact and useful.
- Helpful blueprint even if you do not adopt the platform directly.

### Zep
- Temporal knowledge-graph memory that extracts entities/facts/relationships over time.
- Assembles “just-in-time” context for the agent via retrieval and summarization.
- Strong at handling evolving facts with validity windows and invalidation.

### LangMem (SDK)
- **Semantic**: extract/store facts and preferences from interactions.
- **Episodic**: keep distilled examples for few-shot guidance.
- **Procedural**: optimize agent instructions based on outcomes.

---

## Comparison table

| Framework | Short-term | Long-term | Semantic/Episodic | Procedural | Self-improvement |
|---|---|---|---|---|---|
| Claude Agent SDK | Context + summaries | Files/logs (dev-managed) | Notes + journals | Prompt-driven | Continuity |
| LangGraph + LangMem | State + checkpoints | Namespaces + stores | Facts + cases | Prompt/policy optimize | Retention + evolution |
| CrewAI | RAG recent | SQLite + entity; external providers | Entity facts + results | Static; tool-driven | Accumulate + personalize |
| Google ADK | Session state | MemoryService; Memory Bank | Distilled recall | Prompt/code | Personalize + continue |

---

## How skills differ from memory

**Skills (tools/actions)** are what the agent can *do*: function calls, APIs, retrieval actions, database queries, code execution.  
**Memory** is what the agent *retains*: facts, preferences, prior outcomes, distilled experiences.

- Memory informs **when/how** to use skills, but a skill is an executable capability (not stored information).
- Procedural memory can overlap with skills via rules for tool use, but tools themselves remain skills.

Rule of thumb:
- If the agent fails due to **forgetfulness/inconsistency** → improve **memory**.
- If it fails due to **lack of capabilities** → add **skills/tools**.
