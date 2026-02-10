Comparison of Framework Memory Features
The table below summarizes how each framework addresses different memory types and agent learning:
Short-Term Memory (within session)
Long-Term Memory (across sessions)
Semantic vs Episodic Memory
Procedural Memory (skills/rules)
Self-Improvement Mechanisms
Framework
Claude Agent SDK
Conversation context (limited by context window)�. Optionally uses compaction (summaries) to not exceed window�.
Memory Tool for persistence� – reads/writes files to retain info between runs. Developer can store notes, logs, etc.
No explicit built-in separation; can emulate episodic memory via logs (e.g. progress.txt) and semantic memory by saving extracted facts in files.
LLM’s behavior guided by prompt; no auto-update of rules. Procedural knowledge must be given by developer (or via fine-tuning).
Learns from past via memory files: next session reads what previous session left�. Reduces forgetting by carrying over important context�. No built-in prompt learning loop.
anthropic.com
platform.claude.com
anthropic.com
anthropic.com
platform.claude.com
LangChain LangGraph
Thread-scoped state stored via checkpointing�. Maintains full message history (pruned or filtered if needed) in a conversation thread.
LangMem stores long-term data in custom namespaces�. Supports persistent vector stores or databases for memories accessible in any session.
Explicit types: Semantic memory for facts (e.g. user profile)�, Episodic for past examples�, Procedural for learned rules�. Each handled via specialized APIs (extractors, prompt updates, etc.).
Yes – Procedural memory via prompt updates. LangMem can refine the agent’s system prompt (rules) from interaction feedback��, effectively letting the agent evolve its skills.
Built-in support for lifelong learning: can update memory on-the-fly or in background�. Prompt optimization allows the agent to improve behavior after failures�. Memories (facts/examples) accumulated to avoid relearning things�.
docs.langchain.com
docs.langchain.com
docs.langchain.com
blog.langchain.com
docs.langchain.com
docs.langchain.com
blog.langchain.com
blog.langchain.com
blog.langchain.com
blog.langchain.com
CrewAI
Short-term context with RAG: recent messages/results embedded in ChromaDB for retrieval��. Provides continuity in ongoing tasks.
Long-term SQLite DB to save past task outcomes, insights��. Ensures knowledge is retained across runs. Also entity memory database for persistent info on specific entities�.
Not distinctly labeled, but semantic knowledge is captured in entity memory (facts about people, etc.) and an optional knowledge base. Episodic info is in long-term storage (records of completed tasks = past experiences).
No direct mechanism to alter agent’s core logic. The agent’s “skills” (tools, etc.) are defined in code. Procedural knowledge can be encoded in prompt or tools, but not learned on its own.
Incremental learning by accumulation: Every run can add to long-term memory, so agent references past successes to improve future decisions. If paired with external memory (e.g. Mem0), can adapt to user’s patterns (personalization) over time�. No autonomous policy revision, but avoids repeating mistakes by remembering prior outcomes.
docs.crewai.com
docs.crewai.com
docs.crewai.com
docs.crewai.com
docs.crewai.com
mem0.ai
Google ADK
Session state and event history��. Can persist session via DB to survive restarts�. By default isolated per session unless using special keys to carry over small pieces�.
MemoryService provides long-term memory. In-memory variant (non-persistent) stores raw chat logs (for prototyping)�. Vertex AI Memory Bank (persistent) stores extracted key info with semantic search��.
Semantic memory is achieved via Memory Bank’s distilled facts (e.g. “user’s favorite color is blue”). Episodic memory: the agent can retrieve info from specific past interactions, but mainly through the semantic lens (important events become facts).
No direct procedural memory module. The agent’s methods are static (defined by developer prompts and available tools). ADK does not let the agent rewrite its skill set on its own.
Personalization and context continuity: agent “remembers” user-specific details across sessions with Memory Bank��. Improves responses by recalling past interactions (e.g. avoids repeating explanations). No built-in self-tuning of prompts or model behavior. Any policy improvements require external intervention (developer updates or fine-tuning).
cloud.google.com
cloud.google.com
cloud.google.com
cloud.google.com
cloud.google.com
cloud.google.com
cloud.google.com
cloud.google.com
google.github.io
Standalone Memory Systems and Integration
Beyond the frameworks’ native capabilities, developers often integrate dedicated memory services or libraries into agent workflows. These standalone memory systems focus on providing extended long-term memory, personalization, or advanced retrieval that can plug into any agentic framework. We will look at Mem0, Letta, Zep, and LangMem (SDK) – what they offer independently and how they can be used in agent architectures.
Mem0
Mem0 (pronounced “mem-zero”) is a memory layer designed for long-lived AI assistants with personalization. It treats memory as a first-class component. Mem0’s approach is to infer and store user-specific knowledge from interactions. For example, Mem0 will pick up on patterns like “the user usually prefers reminders at 8 PM” or “they tend to snooze work tasks by 15 minutes”��. It separates the notion of application state (e.g. the list of reminders in a to-do app) from personalization memory (the user’s habits, preferences, and history). In practice, Mem0 uses an LLM under the hood to analyze conversation and usage data and produce structured memory entries. These can be things like preferences (explicit facts about the user) and behavior summaries (statistical or high-level observations about user behavior)��. Mem0 then stores these memories in a database or vector store (Mem0 supports various backends like Qdrant for vectors, with OpenAI or other embedder models)��. Because Mem0 auto-categorizes information, developers can define memory categories – for instance, “personal_information” or custom domains – and Mem0 will file inferred facts accordingly��.
mem0.ai
mem0.ai
mem0.ai
mem0.ai
docs.crewai.com
docs.crewai.com
docs.crewai.com
docs.crewai.com
As an independent tool, Mem0 provides an API (and Python client) where you feed in events (e.g. conversations, user actions) and it updates the memory store. You can then query Mem0 for relevant context to inject into the agent’s prompt. The integration is straightforward: frameworks like CrewAI have a built-in connector for Mem0�, and one can similarly integrate Mem0 into LangChain or Claude by treating it as an external knowledge source. In the Claude RecallAgent example from Mem0’s blog, they combined Claude’s Agent SDK with Mem0: Claude handled the dialogue and tool use, while Mem0 supplied a “mem0_context” object containing the user’s preferences and recent behavior stats to enrich Claude’s prompt��. This resulted in an agent that adapts its suggestions based on the user’s learned habits – for instance, proactively suggesting a reminder time the user often prefers��.
docs.crewai.com
mem0.ai
mem0.ai
mem0.ai
mem0.ai
Memory Types: Mem0 excels at semantic and episodic memory fusion. It keeps raw logs (episodic data) but crucially derives semantic memories (facts like “User is a morning person”) from them. It doesn’t explicitly store step-by-step episodes for the agent to read; rather it condenses them into useful knowledge chunks. Mem0’s memory model can be seen as a form of long-term semantic memory with personalization focus. It likely does not handle procedural memory (it won’t change the agent’s toolset or rules), but it can certainly inform the agent’s procedure by, say, indicating how the agent should tailor its behavior to the user (which the agent’s prompt can incorporate).