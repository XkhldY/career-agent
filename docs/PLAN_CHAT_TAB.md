# Chat Tab – Plan

## Goal

A second UI tab for **chat over jobs**: user asks questions in natural language; the app answers using the jobs in the vector store and shows **citations** with a **“View full job”** link. Design and layout are distinct from the Crawl tab.

---

## 1. User experience

- **Tab navigation:** App has two tabs: **Crawl** (existing) and **Chat**.
- **Chat tab:**
  - Message list: user messages and assistant replies (scrollable).
  - Input at bottom: text field + send (no “Run crawl” style; chat-style submit).
  - Each assistant message can have **citations**: one or more job cards (title, company, snippet or source line) with a **“View full job”** action that opens the full job (same data as Crawl: title, company, Apply link).
- **View full job:** Can be a link to the job URL (external), or an in-app detail using `GET /api/jobs/{id}` or `GET /api/jobs/by-url?url=...`. Plan: use **job URL** for “Apply” and optional **job id** for an in-app “View details” if we add a detail view later; for v1, “View full job” = open job URL in new tab (same as Apply) or a small modal/section that shows title, company, url from the existing API.
- **Empty state:** If there are no jobs in the store, show a short message: “Run a crawl first so I can answer questions about jobs.”

---

## 2. Data flow

1. User sends a message in the Chat tab.
2. Frontend calls **POST /api/chat** with `{ "message": "..." }` (and optionally `conversation_id` for history later).
3. Backend:
   - Embeds the user message (or last message), queries the **vector store** (Chroma) for top-k relevant job documents.
   - Optionally enriches citations with DB: for each retrieved doc, get metadata (url/title/company) from Chroma; if we have `url` in metadata, can call `get_job_by_url(url)` for full record (id, title, company, url) for the response.
   - Builds a prompt for the LLM: system + retrieved job snippets + conversation (user message, and history if we add it). Asks the model to answer based only on the provided jobs and to cite (e.g. by URL or title).
   - Calls **Bedrock** (same region/model pattern as jobs agent) to get the assistant reply.
   - Returns **{ "reply": "...", "citations": [ { "id"?, "url", "title", "company" } ] }** so the frontend can render reply and “View full job” links.
4. Frontend appends the assistant message and its citations to the chat UI.

---

## 3. Backend

### 3.1 Store / retrieval

- **Current:** `VectorStore.retrieve(query, top_k)` returns only `list[str]` (document texts). Chroma also stores `metadatas` with `source`, `title`, `url` when jobs are added.
- **Change:** Add a method that returns **documents + metadata** (and optionally ids), e.g. `retrieve_with_metadata(query, top_k=5)` → `list[dict]` with `document`, `url`, `title`, `chroma_id` (and `id` from DB if we resolve by url). That way we can build citations without an extra DB round-trip per doc, or we can resolve by URL to get the canonical `id` for “View full job” links.

### 3.2 Chat API

- **Route:** `POST /api/chat` (new router, e.g. `app/api/chat.py`, mounted under `/api/chat`).
- **Request body:** `{ "message": "string" }`. Optional later: `conversation_id`, `history`.
- **Behavior:**
  - Validate `message` (non-empty, length limit).
  - Call store `retrieve_with_metadata(user_message, top_k=5)`.
  - If no results: return a short reply like “I don’t have any jobs in the store yet. Run a crawl from the Crawl tab first.” and `citations: []`.
  - Otherwise: build prompt (system: “Answer only from the following job listings. Cite by job title/company/URL.”; user: retrieved docs + “User question: {message}”). Call Bedrock (single completion, no tools). Parse reply; build `citations` from the retrieved items (url, title, company, and id if we fetched from DB).
  - Response: `{ "reply": "...", "citations": [ { "id", "url", "title", "company" } ] }`.
- **Config:** Reuse existing AWS/Bedrock settings; one model id (e.g. Claude Haiku) for chat.

### 3.3 Citations and “View full job”

- Citations come from retrieval metadata (and optional DB lookup by URL). Each citation has at least `url`, `title`, `company`; if we resolve via `get_job_by_url(url)` we also get `id`. Frontend uses `url` for “Apply” / open in new tab and can use `id` for a future `GET /api/jobs/{id}` detail view. For v1, “View full job” = link to `job.url` (same as Apply) or a small inline expansion using existing job API.

---

## 4. Frontend

### 4.1 Structure

- **Tabs:** One component or section for “Crawl” and one for “Chat” (e.g. tab state: `"crawl" | "chat"`). Crawl tab = current page content; Chat tab = new content (message list + input).
- **Chat UI:**
  - Scrollable message list: each item is either `role: "user"` (align right or distinct style) or `role: "assistant"` (reply + citations).
  - Citations: render as small cards (title, company, “View full job” link). Link = `job.url` in new tab, or call `GET /api/jobs/by-url?url=...` and show a tiny modal/drawer with title, company, Apply link.
  - Input: textarea or input + Send button; on submit call `POST /api/chat`, append user message, then append assistant message + citations; disable send while loading.

### 4.2 API client

- Add `postChat(message: string): Promise<{ reply: string; citations: Citation[] }>` and type `Citation = { id?: string; url: string; title?: string; company?: string }`.
- Base URL: same `NEXT_PUBLIC_API_URL` as Crawl.

### 4.3 Design (different from Crawl)

- Chat tab uses a different layout: e.g. full-height chat area, messages in a card or bubble style, citations below or beside the assistant message. Same design system (CSS vars, dark theme) but not the same form-heavy layout as Crawl.

---

## 5. Out of scope for v1

- Conversation history (multi-turn with backend-stored history); v1 can be single-turn only (each request = one user message, no history).
- Resume store and “retrieve same job/resume” (later).
- Streaming reply (optional later).
- In-app job detail page (v1 can rely on “View full job” = external link or small modal with existing API).

---

## 6. Implementation order

1. **Backend: store** – Add `retrieve_with_metadata(query, top_k)` returning docs + url/title/company (and id if from DB).
2. **Backend: chat API** – Implement `POST /api/chat` (prompt, Bedrock call, reply + citations).
3. **Frontend: API** – Add `postChat` and types.
4. **Frontend: tabs** – Add tab switcher; move current Crawl content into Crawl tab.
5. **Frontend: Chat tab** – Message list, input, send; render assistant message and citation cards with “View full job”.
6. **Polish** – Empty state (“Run a crawl first”), loading state, error handling.

---

## 7. Files to add/change (summary)

| Area        | Action |
|------------|--------|
| `backend/app/agents/shared/store.py` | Add `retrieve_with_metadata()` returning list of dicts with document, url, title, (id). |
| `backend/app/api/chat.py`           | New: `POST /api/chat`, orchestrate retrieve → prompt → Bedrock → reply + citations. |
| `backend/app/main.py`               | Include chat router: `app.include_router(chat.router, prefix="/api/chat", tags=["chat"])`. |
| `frontend/src/lib/api.ts`           | Add `postChat`, type `Citation`. |
| `frontend/src/app/page.tsx`         | Tabs (Crawl / Chat); Chat tab = messages + input + citation cards with “View full job”. |

Optional: `frontend/src/components/ChatMessage.tsx` and `CitationCard.tsx` for clarity.
