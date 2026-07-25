# Findings: Chat + Hebrew Learn Polish

## Codebase Exploration Summary

### Chat Panel (`frontend/src/components/ChatPanel.jsx`, 1531 lines)
**Structure:**
- Main component `ChatPanel({ open, onClose, onNavigate, onOpenTab, initialMessage, variant })`
- Two variants: `overlay` (fixed popup, Ctrl+P) and `tab` (inline in main content)
- Session persistence via localStorage + server-side conversation CRUD
- Prebuilt responses for common questions (bypasses LLM)
- Verse ref detection with 4 regex passes + book name mapping (100+ aliases)
- Response mode system: auto/short/medium/deep → maps to max_tokens 4K/32K/128K
- Tool category toggles for 7 groups (lookup, search, connections, graph, gematria, study, staging, learning)
- Edit/resend with inline textarea
- Cost tracking with model/usage display

**Key files:**
- `frontend/src/components/ChatPanel.jsx` — all chat UI + client logic
- `frontend/src/api.js` — `chat()` function (lines 229-240) sends POST to `/api/v1/chat`
- `web/routes/chat.py` (1398 lines) — LLM proxy with function calling (DeepSeek)
- `CHAT_AGENTS.md`, `CHAT_AGENTS_HEBREW.md`, `CHAT_AGENTS_KNOWLEDGE.md` — system prompts

**Known bugs:**
1. **Thinking display bug** (backend line 1349): `final_content = choice["message"]["content"] or choice["message"].get("reasoning_content") or ""` — when DeepSeek returns empty `content` with `reasoning_content`, the backend copies reasoning into content. Frontend then displays it twice: once in main body, once in `<details>` thinking block.
2. **Copy-all toggle** (frontend line 1453-1457): "Copy all" and "✓ Copied" can appear simultaneously because the button text switches in-place but the parent visibility check is wrong.
3. **Token info on EVERY message** — clutters the conversation. Should only show on last assistant message.

### Hebrew Learn (`frontend/src/components/HebrewLearnView.jsx`, 668 lines)
**Structure:**
- Main component `HebrewLearnView({ onOpenLesson, onOpenPassage })`
- Fetches curriculum + gamification in parallel via `Promise.all`
- 102+ lessons across 9 categories with mastery tracking
- Multiple modes (switchable via state variables):
  - Curriculum list view → mastery map
  - PassageReader, VerbDrills, HebrewReview (Anki), DailyVerse, AudioReview, Quiz, QuickSession, FreqVocab
- Gamification: XP, streak, badges (server-side, `hebrew_gamification` table)

**Key files:**
- `frontend/src/components/HebrewLearnView.jsx` — dashboard/curriculum
- `frontend/src/components/HebrewLessonView.jsx` — single-lesson view
- `frontend/src/components/HebrewQuiz.jsx` — quiz component
- `frontend/src/components/HebrewQuizCard.jsx` — quiz card rendering
- `frontend/src/components/HebrewVerbDrill.jsx` — verb conjugation drill
- `frontend/src/components/HebrewPassageReader.jsx` — passage reading mode
- `web/routes/hebrew.py` (1300+ lines) — curriculum, FSRS, gamification API
- `frontend/src/lib/card-factory.js` — card generation for reviews

**Pain points:**
1. **Action button overload** (lines 398-476): 10+ `<button>` elements in a single `flex-wrap` container. On desktop they wrap into 3-4 rows. On mobile they overflow.
2. **No next-lesson flow**: After completing a lesson (`setHebrewLessonId(null)` drops back to curriculum), there's no "you should study X next" guidance.
3. **Mobile layout**: Category filter tabs wrap awkwardly on small screens. The action bar is unusable on mobile.

### Quality Baseline
- Structural quality: 0.4211 (scanned 1298 files, 565 import edges)
- No architectural violations detected

## Pre-resolved Decisions

### Decision: SSE streaming over WebSocket
- **Rationale:** SSE is simpler (one-directional, HTTP-native), works through proxies, no special server setup. FastAPI supports SSE via `StreamingResponse`. WebSocket would add complexity (connection management, reconnection logic) without benefit for this use case.
- **Tradeoff:** SSE is server→client only, but we only need to stream from server to client.

### Decision: No new client dependencies
- **Rationale:** Keep the frontend lean. `fetch` + `ReadableStream` are natively supported in all modern browsers for SSE-like streaming. No need for `eventsource-parser` or similar.

### Decision: Fix thinking display at source (backend)
- **Rationale:** The bug is in backend line 1349 where `reasoning_content` leaks into `content`. Fixing it at source prevents the bug everywhere (including any future consumers of the API). Frontend gets a safety check too.

### Decision: Dropdown menus for Hebrew action bar
- **Rationale:** 10+ buttons is too many for any screen. Grouping into 3 thematic dropdowns (Practice, Reading, Tools) maintains access while drastically reducing visual clutter. Native `<details>` elements avoid JS complexity.

## Files to Modify

| File | Track | Est. Changes |
|------|-------|-------------|
| `web/routes/chat.py` | A1 | +100 lines (SSE endpoint + thinking fix) |
| `frontend/src/api.js` | A2 | +30 lines (chatStream function) |
| `frontend/src/components/ChatPanel.jsx` | A2, B1, B2 | +120 lines changed |
| `frontend/src/components/HebrewLearnView.jsx` | C1, C2, C3 | +120 lines changed |
| `frontend/src/components/HebrewLessonView.jsx` | C2 | +20 lines |
