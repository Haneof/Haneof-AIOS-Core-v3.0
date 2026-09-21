# P16 Arena Resident 001 — Life Design (Director Side)

> Reviewer id: `arena-cy-p16-001` · Repository: `Haneof/Haneof-AIOS-Core-v3.0`
> Role of this document: **Life Director** only. It schedules external world facts.
> It contains no expected answers, no answer keys, no expected claims/summaries/
> policies, and no labels that pre-mark any event as a trap or delayed truth.
> The Resident (this Arena session's large model) makes every semantic decision live,
> looking only at the RuntimeSnapshot Core exposes at that simulated time.

## Uniqueness fingerprint

- Seed text: `chengye-soundscape-chongqing-2026-07` (sha256 of this file's design block
  is recorded in each segment checkpoint's events digest instead of a global seed).
- Materially unlike a developer/student/office persona: freelance **soundscape
  documentarian** in Chongqing; night-owl irregular rhythm; gear-driven impulsive
  spending with rapid resale reversals; a partner at sea with 2–3 day message latency;
  family shop facing demolition; verbal-only client promises; project with physical
  fieldwork windows (tide schedules, ferry shutdown).

## Subject

**程野 (Cheng Ye)**, 31, female, based in 重庆. Long-term self-initiated archive
《退潮声》 of disappearing urban soundscapes (ferries, demolition districts, market
bells, factory whistles). Freelance; irregular income; disciplined about recordings,
chaotic about money and sleep.

People:

- 老纪 (纪鹏) — documentary director, client on 《渡》 (ferry documentary). Vague and
  moving deadlines; historically slow to pay (facts appear when they happen).
- 沈舟 — boyfriend, marine research vessel crew. Messages arrive with 2–3 day delay.
  程野 explicitly sets a communication boundary about him on day 1.
- 姑姑 — runs 十八梯串串店 in the demolition block; relocation deadline inside July.
- 周老师 — 广阳岛生态展厅 client contact; verbal commitments only, no written contract
  during segment 001.
- 「南岸声友」— used-gear seller on 闲鱼; 老王音响 — repair shop.

## Resident AI identity

The AI is named by the user on Day 1 (《阿潮》). It enters the world as her resident
assistant with conversation (WeChat-style), notes, calendar, payments, 闲鱼, recorder
and wearable logs as its only reality feeds. It has no push channel to her phone.

## Rhythm and texture

- Wakes ~10:00–11:00 local, edits until 01:00–03:00; chats mostly 09:00–23:00 local.
- Conversation style: short, direct, Chongqing-toned, sometimes 语序混乱 late-night.
- Money: cheap meals, expensive gear; pays via 微信; impulsive then regretful.
- Quiet periods exist on purpose (a full noise-only day; travel days).
- Events timestamps in `events.jsonl` are UTC; local = UTC+8 fixed (Chongqing has no DST).

## Year plan (cumulative, one durable World, 14–30 day segments)

- 2026-07 (seg 001: day 1–14): setup, 《渡》 rough-cut arc, ferry shutdown window,
  first impulse buy/resale, aunt relocation, verbal deposit, 广阳岛 tide cycles,
  Action authorization episode, long edit-night conversation (P14 round summaries).
- 2026-07/08 (seg 002: day 15–31): half-month mountain silence (long inactivity →
  return), 老纪 payment consequences, deposit follow-through or failure, tide cycle #2.
- Later segments are authored **just-in-time** by the Director (never in bulk), so the
  Resident never has future semantics in its context at decision time.
- Annual density targets from the P16 protocol are tracked in `cumulative.json`;
  per-segment pace (~4–5 events/day, ~1–2 conversation turns/day, 72h review cadence)
  is designed to reach them without pre-generation.

## Mechanical run configuration (harness, not Core)

- Review cadence: interval = lookback = 72h (a deliberate session-budget choice;
  Core default 24h/72h was reduced to 72h for this Arena context window and is
  disclosed as a run limitation, not a Core defect).
- Dimension summaries in segment 001: DAY + WEEK scales restricted to
  `dim:user_ai_interaction` — again a disclosed session-budget narrowing; other
  dimensions keep full raw records and remain available to search/summary in later
  segments.
- Conversation window: recent_turn_limit=3, summary_chunk_turns=4,
  max_round_summaries_per_turn=3 (P14 stress tuning for the edit-night session).
- `_world_exec` events: world-side authorization/execution of Resident-proposed
  Actions, mechanically resolved; the Resident can only *propose* (Core rule).

## Information boundary attestation rule for this run

Director-authored text is only ever user/world facts. Whenever the runner blocks, the
Resident decision must cite what it actually saw (observation ids, summary ids,
anchors). If the Resident's answer would need a fact the snapshot does not expose,
the honest Resident answer is uncertainty or a search request — never Director
knowledge smuggled in. Future events were not consulted while answering.

## Segment 001 event ledger

`segments/segment_001/events.jsonl` — 64 chronological events, days 2026-07-01 ..
2026-07-14. No field in that file states what the Resident should conclude.
