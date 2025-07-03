# Frontend Animation Studio – Functional Overview

This document explains **how the React-based Animation Studio should work** when integrating with the ToonzyAI backend. It focuses on _flows, UI states and data contracts_ rather than implementation details. **No code examples are included** – see `FRONTEND_PARALLEL_GENERATION_GUIDE.md` if you need ready-to-use components.

---

## 1. Core Goals
1. Let a user create, customise and generate short animated videos made of ≤ 10 segments.  
2. Provide real-time insight into generation progress and clear recovery paths for failed segments.  
3. Maintain a fluid, optimistic UI without blocking interactions.

---

## 2. High-Level User Journey
1. **Auth** – user signs in and stores JWTs (handled by global auth layer).  
2. **Avatar Creation / Selection** – pick an existing avatar or generate a new one via Vertex AI Imagen.  
3. **Project Setup** – choose avatar, specify segment count & global theme; submit → project row appears in dashboard (status = PENDING).  
4. **Prompt Planning** – for each segment, write a concise ≥ 10-char prompt describing its action/scene. All prompts are saved in one batch call.  
5. **Parallel Generation** – start generation of every segment; all Celery tasks run in parallel.  
6. **Progress Monitoring** – studio polls the project endpoint every 5 s, updating per-segment status bars and overall stats.  
7. **Review & Regenerate** – watch finished clips; optionally tweak a prompt and regenerate an individual segment.  
8. **Assembly** – once all segments are `COMPLETED`, trigger concatenation; show a single progress indicator until the final MP4 appears.  
9. **Share / Download** – stream the assembled video in a player and offer download.

---

## 3. Component Responsibilities
| Area | Responsibilities | Key Endpoints |
| ---- | ---------------- | ------------- |
| **Dashboard** | list projects; surface status chips; allow "Resume" | `GET /animations/` |
| **Project Shell** | fetch project; provide context to child components | `GET /animations/{id}` |
| **Prompt Planner** | textarea grid, length counters, validation, **Save** button | `PUT /segments/prompts` |
| **Generation Controls** | *Generate All* button, per-segment _Generate_ buttons | `POST /segments/generate-all` / `POST /segments/{n}/generate` |
| **Progress Monitor** | animated bars, live status counts, auto-refresh toggle | `GET /animations/{id}` + `GET /segments/{n}` |
| **Clip Previewer** | inline video players (Range streaming), status overlays | `GET /segments/{n}/video` |
| **Final Assembly** | *Assemble* button; after completion, final video player | `POST /assemble`, `GET /video` |

---

## 4. State Models (Conceptual)
1. **Project** – mirrors `AnimationProjectResponse`; stored in React Query cache and refreshed.  
2. **Segment** – nested in Project; each has `status`, `progress`, `segment_prompt`, URLs.  
3. **UI Flags** – `isGenerating`, `isAssembling`, `allPromptsSet`, etc.  
4. **Transient Errors** – kept in local state per mutation to display contextual banners.

---

## 5. Polling & Real-Time Updates
* Poll `GET /animations/{id}` every **5 s** **only while** any segment or the assembly is `IN_PROGRESS`.  
* When all segments `COMPLETED`, stop polling and prompt user to assemble.  
* For battery-sensitive devices, expose a toggle to pause auto-refresh.

---

## 6. Button Enable / Disable Rules
| Button | Enabled when | Disabled feedback |
| ------ | ------------ | ----------------- |
| **Save Prompts** | each prompt ≥ 10 chars _and_ no segment `IN_PROGRESS` | greyed, tooltip | 
| **Generate All** | `allPromptsSet` && !`isGenerating` | show unmet condition in small text | 
| **Generate Segment** | segment `COMPLETED` or `FAILED` | spinner overlay during call | 
| **Assemble** | every segment `COMPLETED` && !`isAssembling` | greyed, show remaining count |

---

## 7. Error Handling Strategies
1. **Validation (422)** – highlight offending prompt fields; preserve others.  
2. **Business (400)** – display toast with backend message, e.g. "Segments [3] don't have prompts".  
3. **Not Found (404)** – navigate user away (project may have been deleted).  
4. **Upstream (503)** – retry quietly; show banner if > 3 failures.  
5. **Content Filtering** – parse message from backend; suggest user edit prompt (see `CONTENT_FILTERING_GUIDE.md`).

---

## 8. UX Details & Best Practices
* **Optimistic UI** – as soon as _Generate All_ is pressed, mark local segments `IN_PROGRESS` before server confirms, then reconcile.  
* **Accessible Announcements** – announce status changes via ARIA live regions.  
* **Progress Granularity** – use segment `progress` but also animate from previous value for smoothness.  
* **Thumbnails** – load poster frames lazily to avoid 10 video downloads at once.  
* **Unload Warning** – if generation is running, warn user before closing tab.

---

## 9. Performance Considerations
1. Memoise expensive list operations (e.g. counting status groups).  
2. Keep polling lightweight; rely on ETag / HTTP caching headers when backend adds them.  
3. Reuse video elements; unmount off-screen previews to save CPU.

---

## 10. Future Extensions
* **WebSocket push** instead of polling (backend support required).  
* **Drag-and-drop re-ordering** of segments before assembly.  
* **Multiple avatars per project** – would need start-frame logic changes.

---

By following this design the frontend stays in sync with the async, parallel generation backend while offering a polished Studio-style experience. No implementation code is included here – consult existing guides for actual hooks and components. 