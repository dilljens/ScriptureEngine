# Polish: Chat + Hebrew Learn

**Goal:** Make the chat and Hebrew learning features look better and work better.

**Quality baseline:** 0.4211 (structural quality)

---

## Requirements

- [ ] R1: Chat streaming — real-time response display via SSE, no more 2-8 minute silent waits
- [ ] R2: Chat thinking display fix — reasoning_content no longer shown in wrong place or duplicated
- [ ] R3: Chat multi-line input — compose longer messages with line breaks
- [ ] R4: Chat visual refresh — better message bubbles, avatars, smoother UX
- [ ] R5: Hebrew action bar reorganization — collapse 10+ buttons into clean dropdown menus
- [ ] R6: Hebrew guided next-lesson flow — suggest logical next lesson after completion
- [ ] R7: Hebrew LearnView mobile layout polish

## Pre-resolved Decisions

- **Streaming approach:** Server-Sent Events (SSE) via new `/api/v1/chat/stream` endpoint. Backend yields `data: {"type":"thinking","content":"..."}` and `data: {"type":"text","content":"..."}` events. Frontend reads with `fetch` + `ReadableStream` (no extra deps).
- **No new client dependencies:** Use native `EventSource` or `fetch` streaming. No SSE library, no WebSocket.
- **CSS-only for animations:** Use Tailwind `animate-*` utilities. No Framer Motion or animation library.
- **Thinking display:** Fix at source (backend line 1349). Never use reasoning_content as content fallback.

---

## Track A: Chat — Streaming & Display Fixes `[ ]`

- 📏 Scope: ~2 files, ~150 lines changed
- Description: Add SSE streaming endpoint, fix the thinking/reasoning display bug, rework the frontend to consume streaming chunks in real-time

### Phase A1: Backend SSE streaming endpoint `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 8
- [ ] Add `/api/v1/chat/stream` route in `web/routes/chat.py` that yields SSE events
- [ ] Yield `data: {"type":"thinking","content":"..."}` for reasoning_content from DeepSeek
- [ ] Yield `data: {"type":"text","content":"..."}` for each content chunk
- [ ] Yield `data: {"type":"tool_call","tool":"name","args":{...}}` during tool execution
- [ ] Yield `data: {"type":"done","usage":{...},"cost":{...}}` when complete
- [ ] Fix the thinking/content bug: change line 1349 to not use reasoning_content as content fallback
- 📏 Scope: ~1 file (`web/routes/chat.py`), ~100 lines
- ✅ Checkpoint: `python3 -c "import httpx; r=httpx.get('http://localhost:8000/api/v1/chat/stream', json={'messages':[{'role':'user','content':'hi'}]}, timeout=30); print(r.status_code, r.text[:200])"` returns 200 with SSE events
- ⚙ Fallback: If SSE is too complex, fall back to chunked JSON response and poll on frontend

### Phase A2: Frontend streaming consumer `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 6
- [ ] Add `chatStream(messages, opts)` function to `frontend/src/api.js` — returns ReadableStream parser
- [ ] Replace `performChat()` in ChatPanel.jsx to consume streaming chunks
- [ ] Update `waiting` state to show real-time content instead of bouncing dots
- [ ] Show thinking content LIVE as it arrives (in the details block or inline)
- [ ] Apply safety: if `reasoning_content === content`, don't show thinking section separately
- 📏 Scope: ~2 files (`frontend/src/api.js`, `frontend/src/components/ChatPanel.jsx`), ~80 lines
- ✅ Checkpoint: Send a message in chat, verify text appears character-by-character, thinking appears live
- ⚙ Fallback: Keep non-streaming path as fallback; detect if stream endpoint 404s

## Track B: Chat — Input & Visual Polish `[ ]`

- 📏 Scope: ~1 file, ~100 lines changed
- Description: Multi-line input, better message display, avatars, smoother UX

### Phase B1: Multi-line input with context tray `[ ]`
- 🏷 Priority: medium
- 🔁 Max turns: 4
- [ ] Replace `<input type="text">` with `<textarea>` in ChatPanel.jsx
- [ ] Enter sends, Shift+Enter = newline, Ctrl+Enter sends
- [ ] Auto-resize textarea as content grows
- [ ] Add a visible "context tray" above the input showing attached verses/chapter as removable chips
- 📏 Scope: ~1 file, ~40 lines
- ✅ Checkpoint: Type a multi-line message, verify Enter sends, Shift+Enter adds newline
- ⚙ Fallback: Keep input hidden behind a toggle, default to single-line

### Phase B2: Visual message refresh `[ ]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [ ] Add user/assistant avatars (letter-in-circle for user, 🤖 or "SE" for assistant)
- [ ] Smoother message bubble styling with subtle shadows and animations (slide-in)
- [ ] Better copy button: tooltip + icon that doesn't require hover on mobile
- [ ] Show token/cost info ONLY on last assistant message (not every message) — declutter
- [ ] Fix "Copy all" toggle — currently both "Copy all" and "✓ Copied" can show simultaneously
- 📏 Scope: ~1 file (`ChatPanel.jsx`), ~60 lines
- ✅ Checkpoint: Visual check — messages look clean, copy works, token info only on last message
- ⚙ Fallback: Skip animations if Tailwind animate utilities cause issues

## Track C: Hebrew Learn — Action Bar & Navigation `[ ]`

- 📏 Scope: ~1 file, ~120 lines changed
- Description: Collapse 10+ action buttons into dropdown menus, add guided next-lesson flow

### Phase C1: Action bar reorganization `[ ]`
- 🏷 Priority: high
- 🔁 Max turns: 5
- [ ] Group 10+ buttons into 3 dropdown menus:
  - **Practice** dropdown: Quick Session, Quiz, Review
  - **Reading** dropdown: Verse of Day, Read Passage
  - **Tools** dropdown: Verb Drills, Top Vocab, Audio Review
- [ ] Keep Map/List toggle as a standalone small button
- [ ] Ensure dropdowns work on mobile (touch-friendly)
- [ ] Clean up the action bar spacing and responsive layout
- 📏 Scope: ~1 file (`HebrewLearnView.jsx`), ~60 lines
- ✅ Checkpoint: All actions accessible via dropdown menus on desktop and mobile
- ⚙ Fallback: If dropdowns feel wrong, use a secondary action row with compact icon buttons

### Phase C2: Guided next-lesson suggestion `[ ]`
- 🏷 Priority: medium
- 🔁 Max turns: 4
- [ ] After a lesson is completed (return from `HebrewLessonView`), show a "Continue Learning" card
- [ ] Suggest next lesson: first unlocked with lowest mastery, or next in same level/category
- [ ] Add a "Continue" button that opens the suggested lesson directly
- [ ] Show progress: "You've mastered X of Y lessons in this category"
- 📏 Scope: ~1 file (`HebrewLearnView.jsx`, `HebrewLessonView.jsx`), ~60 lines
- ✅ Checkpoint: Complete a lesson, see a next-lesson suggestion card
- ⚙ Fallback: Show a simple "next up" line in the lesson list instead of a card overlay

### Phase C3: Mobile layout polish `[ ]`
- 🏷 Priority: low
- 🔁 Max turns: 3
- [ ] Make category filter tabs horizontal-scrollable on mobile
- [ ] Reduce padding/margins on small screens
- [ ] Ensure mastery map grid adapts (2 columns on mobile, 8+ on desktop)
- 📏 Scope: ~1 file (`HebrewLearnView.jsx`), ~20 lines
- ✅ Checkpoint: Hebrew Learn view looks good on 375px width viewport
- ⚙ Fallback: Skip mobile polish if it interferes with desktop layout

## Track D: Quality & Final Verification `[ ]`

- 🏷 Priority: medium
- 🔁 Max turns: 3
- [ ] Run `sentrux_scan` to compare quality against baseline (0.4211)
- [ ] Run LSP diagnostics on changed files — no regressions
- [ ] Verify all checkpoints pass
- [ ] Commit with message `polish: chat streaming, multi-line input, visual refresh; hebrew action bar and guided lessons`
- 📏 Scope: ~1 file (progress)
- ✅ Checkpoint: All phase checkpoints pass, quality signal >= 0.42
- ⚙ Fallback: If quality degraded, revert or fix the specific violation
