# Game log observations

Notes from a full pass over the 14 played games: `logs/game_summary.jsonl`, `logs/games/0001-0014.json` (structural detail), and `logs/traces/0002-0014.jsonl` (raw prompts/responses; game 1 has no trace file). Each entry below names exactly which file, game, and caller it came from, so it can be re-checked or extended later without re-deriving it from scratch.

## 1. The 14 played games are not a random sample of the 840-game design (important)

`tournament/schedule.py::generate_schedule()` builds the full 840-row schedule with `itertools.combinations(range(8), 2)` over a fixed `PATTERNS` list, in lexicographic order, and never shuffles it. `next_pending()` in the same file always returns the first row whose status is still `"pending"`. The result is that games are played in exactly the order the nested loops produce them, not a random draw from the design space.

Checked against the actual role assignments in `logs/game_summary.jsonl` for all 14 games:

| game | werewolves | seer | doctor |
|---|---|---|---|
| 1-5 | Baseline, Reflection | ReAct | ToT, Baseline2, Reflection2, ReAct2, ToT2 (in that order) |
| 6-10 | Baseline, Reflection | ToT | ReAct, Baseline2, Reflection2, ReAct2, ToT2 (in that order) |
| 11-14 | Baseline, Reflection | Baseline2 | ReAct, ToT, Reflection2, ReAct2 (in that order, one game short of a full block) |

Two consequences:

- **Every werewolf, in every one of the 14 games, has been Baseline or Reflection.** ReAct and Tree of Thoughts have not played werewolf once in the current dataset. Any statement about "which architecture is a better or worse werewolf" is untested for two of the four patterns.
- Seer and doctor assignments are walking through the same fixed sequence, five or so games at a time, rather than being sampled. `detection_accuracy`, `survival_avg`, and the win-rate figures currently in the README describe this one narrow, deterministic slice of the design space, not a representative draw from it.

This doesn't need a code fix to keep playing toward 840 (it'll cover everything eventually by construction), but it matters for any conclusion drawn from a partial run, which is exactly the situation the project is in at 14/840. Before the next batch, or before drawing further conclusions from an in-progress run, `generate_schedule()`'s rows should be shuffled once (or `next_pending()` should draw randomly among pending rows) so a snapshot taken at any point in the run stays representative.

## 2. Token and time growth, full dataset (not just the two-game example already in the README)

The README's "How the design evolved" section cites one call type going from 781 to 3,296 tokens between an early and a late game. The same trend holds across every game, more sharply:

| game | total tokens | total calls | elapsed sec |
|---|---|---|---|
| 1 | 93,566 | 94 | 110.0 |
| 2 | 135,109 | 118 | 150.3 |
| 3 | 201,872 | 126 | 192.4 |
| 4 | 137,771 | 100 | 179.0 |
| 5 | 167,671 | 123 | 270.8 |
| 6 | 197,633 | 126 | 217.6 |
| 7 | 173,551 | 117 | 207.7 |
| 8 | 129,475 | 95 | 166.1 |
| 9 | 226,696 | 130 | 221.0 |
| 10 | 542,229 | 157 | 448.7 |
| 11 | 845,769 | 201 | 509.2 |
| 12 | 1,071,781 | 226 | 588.0 |
| 13 | 1,112,251 | 228 | 616.7 |
| 14 | 818,801 | 210 | 706.6 |

Total tokens grew roughly 12x from game 1 to game 13, while call count only grew about 2.4x (94 to 228), so most of the growth is per-call prompt size, not call frequency. There's a clear step change at game 10, tokens roughly triple between game 9 and game 10 with call count barely moving, meaning something about the context each agent receives changed meaningfully right around that point. Elapsed time grew even faster than tokens (110s to 706s, about 6.4x), consistent with longer prompts costing more than linear time to process.

Source: `logs/game_summary.jsonl`, field `api.total_tokens` / `api.total_calls` / `api.total_elapsed_sec` per game.

## 3. The engine kept evolving after game 14, in ways the 14 logs can't show

`game/engine.py` currently builds a result dictionary that includes `night_actions`, `passes`, `bids`, `vote_accuracy`, and `vote_accuracy_by_pattern` (see the dict literal around line 420-459). None of these fields exist in any of the 14 persisted `logs/games/*.json` files, whose `result` object only has `winner, rounds, eliminations, detection_accuracy, survival_avg_rounds, api, call_log, speeches, votes`.

`tournament/logger.py::write_game_log()` writes whatever `result` dict it's handed via `{**result, "call_log": clean_call_log}`, it doesn't filter out `night_actions`/`passes`/`bids` itself. So the only explanation is that this part of `engine.py` was extended after game 14 was played (2026-05-18T18:05:16, the last timestamp in `game_summary.jsonl`), and no game has been run since to pick up the richer schema. Concretely, this means:

- Bid values (0-5, per player per discussion round) were never captured for any of the 14 games, only their effect (who spoke in what order) is visible.
- Vote reasons (the engine already models a `reason` field per vote, per the current `to_dict`) don't exist in the logged data either, `logs/games/*.json`'s `votes` entries only have `round`, `voter_id`, `target_id`.
- The next batch of games, run under the current code, will produce noticeably richer per-round data than anything analyzed so far.

## 4. Format-recovery events (the engine repairing malformed LLM output)

Searching all 13 trace files for callers containing `format_retry` found 9 occurrences, concentrated late:

- `0009.jsonl`: 1 (`Eve[ReAct].night.format_retry`)
- `0010.jsonl`: 1 (`Eve[Reflection].vote.format_retry`)
- `0011.jsonl`: 1 (`Hank[ReAct].night.format_retry`)
- `0012.jsonl`: 6 (`Grace[ReAct].vote.format_retry`, `Eve[Baseline].vote.format_retry`, `Frank[Reflection].vote.format_retry`, and three more)

All 9 are in games 9-12, the same games where prompt size was climbing fastest (see #2). This is a concrete, if small, signal that heavier context made it harder for the model to keep returning cleanly parseable output, and that the engine has a real repair path for when that happens rather than crashing or silently misresolving.

## 5. No self-protecting doctors, checked directly

Cross-referenced each game's doctor (identified from the `"You are the doctor"` system-prompt marker in the traces) against their own final night-action response, across all 13 traced games (23 recoverable night decisions total; a few Tree of Thoughts `.night.eval` responses don't contain a parseable name and were skipped). Zero instances of a doctor choosing themselves as the protection target.

## 6. No self-votes at the engine level, confirmed across the full dataset

`voter_id == target_id` never occurs in any of the 14 games' `votes` records. This matches the previously-identified mechanism in `game/engine.py`'s `_find_player(exclude_id=...)`, which structurally prevents a self-vote from resolving even if the raw LLM text suggested one. Checked exhaustively this time (all 14 games, not a sample), same conclusion as before.

## 7. Checked and ruled out: no genuine LLM refusals or character breaks

Searched every trace response for refusal-style phrases (`as an ai`, `i cannot`, `i'm sorry`, `language model`, etc.). The only hits (9, across games 7, 8, 9, 12, 13) were all ordinary in-character idioms, "I can't help but feel...", "I can't shake off a suspicion...", not safety refusals or breaks in character. Recorded here so this doesn't need re-checking later.

## 8. False alarm, ruled out: no real encoding/mojibake bug

An early pass over `logs/games/0002.json` appeared to show corrupted characters (a replacement character in place of an apostrophe and an em dash in a tool description). Re-checked directly against the raw UTF-8 bytes of the file and against `logs/traces/*.jsonl` with a script that counts the actual character, zero occurrences in either. The corruption was in how a Windows terminal (cp1254 code page) was displaying the text during analysis, not in the project's actual data. Worth recording since it looked real at first glance.

## Suggested follow-ups (not implemented, just flagged)

- Shuffle the schedule (or randomize which pending row is picked next) before running more games, so any future snapshot of an in-progress run is representative across werewolf pairs, not a fixed slice of them (see #1).
- The richer fields the engine can now produce (`bids`, `passes`, per-vote `reason`) are worth capturing from game 15 onward; they'd let future analysis look at bidding behavior and stated vote reasoning directly instead of only inferring it from speeches.
