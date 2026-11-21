# Munshi architecture decisions

## Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED
- **Transport:** GPT-Live (`gpt-live-1.1`) over browser WebRTC, **client delegation**. The backend creates the session (`client.live.create`) from the browser's SDP offer, so the API key never reaches the browser.
- **Server control:** a Python sideband (`client.live.sideband.connect(session_id=...)`) receives `session.input_transcript.delta`, `session.delegation.created` and other events, runs the OpenAI Agents SDK agent, and replies with `session.commentary.append`.
- **Browser data channel is locked down:** it may send only `session.close`, and receives only captions and lifecycle events (`client.data_channel` allow-lists).
- **Confirmation mechanism:** a spoken "yes" counts only when the server itself heard it on the sideband transcript (`voice_turns`), arrived after the preview was presented, and passes the deterministic affirmation classifier. A Confirm button (cookie + CSRF) is always available as well.

### Evidence (local spike, `spikes/voice_spike`, synthetic fixture)
| Step | Observed |
|---|---|
| Sideband attached | `live_u23_…eWOtA1t7` |
| Server-observed user speech | "Travel budget mein kitna bacha hai" |
| Delegation | `session.delegation.created` at offset 3,800 ms |
| Agent tool call | `get_budget_status` (Agents SDK, `gpt-5.4-mini`), 5.37 s |
| Spoken result | "Travel budget mein ₹45,000 bacha hai." |

Follow-up: reduce delegation latency (currently ~5 s), e.g. with low reasoning effort and a quiet `thinking.append` acknowledgement.
