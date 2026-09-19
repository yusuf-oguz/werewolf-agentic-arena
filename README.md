# Werewolf Agentic Arena

<details>
<summary>🇹🇷 Türkçe özet için tıklayın</summary>

**Amaç:** Aynı LLM üzerinde, dört standart agentic akıl yürütme mimarisini (Baseline, Reflection, ReAct, Tree of Thoughts) Werewolf (Vampir Köylü) oyununda karşılaştırmak. Oyun ortamının kendisi büyük ölçüde var olan çalışmalardan uyarlandı: bidding tabanlı konuşma sırası Werewolf Arena'dan, oyun durumu tasarımı Xu vd.'den. Bu projenin kattığı şey oyunu yeniden icat etmek değil, dört farklı akıl yürütme desenini (her biri kendi prompt ve araç tasarımıyla) bu ortama uyarlayıp aynı koşullarda karşılaştırmak.

**4 mimari karşılaştırılıyor:** Baseline (kontrol grubu), Reflection (taslak → eleştiri → yeniden dene), ReAct (düşün → oyun durumu araçlarını sorgula → uygula), Tree of Thoughts (çoklu dal üretimi + değerlendirici seçimi).

**Uyarlama süreç içinde gelişti:** Oyun durumu temsili (bağlam zenginliği) geliştikçe, oyuncu kalitesi de değişti. Aynı çağrı türü için (ToT oy stratejisi) prompt uzunluğu erken oyunlarda 781 token iken geç oyunlarda 3296 tokene çıktı. Somut bir örnek: geç bir oyunda Reflection deseniyle oynayan bir kurt adam (Carol), önce masum bir oyuncuyu ustaca hedef gösterip elettirdi, kendisi şüphelenilince aynı retorik hamleyi tam tersine çevirip şüphelenen kişiye karşı kullandı; çok turlu, tutarlı bir blöf.

**Durum: proje burada tamamlandı.** 14 oyun oynandı (840 oyunluk dengeli tasarımın küçük bir kısmı), ve proje bilinçli olarak burada sonlandırıldı: dört deseni ortama uyarladıktan sonra istatistiksel olarak anlamlı bir karşılaştırma için mimari başına yüzlerce oyun gerekiyor, oysa token maliyeti oyun başına milyonlara çıkmış durumda (13. oyun tek başına 1,1 milyon token). Mevcut 14 oyundan: Kurt Adamlar %71.4 kazandı (10/14), ToT bir oyunda Baseline'a göre ortalama ~3.8× daha fazla LLM çağrısı kullanıyor.

</details>

---

This project implements and compares four standard agentic reasoning patterns (Baseline, Reflection, ReAct, Tree of Thoughts) on the same LLM, in a Werewolf (Mafia) environment. The environment itself is largely adapted from existing work, not invented here: bid-based turn order comes from Werewolf Arena (Bailis et al., 2024), the game-state design from Xu et al. (ICML 2024). What this project adds is adapting four distinct reasoning patterns to that environment, each with its own prompt and tool design, and running them under matched conditions, holding the model fixed while the architecture varies. The same setup could, in principle, be pointed the other way, fixing the architecture and comparing models instead.

## Why Werewolf as a benchmark

Most agentic-architecture comparisons test different LLMs on one fixed architecture, or pit one new architecture against a couple of ad hoc baselines. There's no controlled, published sweep of standard agentic patterns (Baseline, Reflection, ReAct, Tree of Thoughts) run on the same LLM in the same environment, which is the gap this project starts with. Werewolf is a strong candidate for this kind of comparison: it demands private information, deception, coalition-building, and reasoning that compounds across multiple rounds, properties that separate architectures from each other far more sharply than a single-turn QA benchmark would.

Werewolf Arena (Bailis et al., 2024) and Xu et al. (ICML 2024) already did the environment design work, bidding-based turn order and game-state representation respectively. Neither implemented and compared Reflection and Tree of Thoughts alongside ReAct and a plain baseline, on the same environment, on the same LLM. That's what this project adapts them for: each pattern needed its own prompt structure (a critic loop for Reflection, a tool set for ReAct, parallel branches plus an evaluator for ToT), built on top of the borrowed environment rather than a new one.

## Four architectures compared

| Pattern | Mechanism |
|---|---|
| **Baseline** | Direct prompt to action. The control group. |
| **Reflection** | A generator LLM drafts an action, a critic LLM evaluates it for consistency, role safety, and persuasiveness, and retries if needed. |
| **ReAct** | Think, query the game-state tools (vote history, conversation log, survivors, suspicion graph, elimination history), observe, think again, act. |
| **Tree of Thoughts** | A generator produces multiple parallel branches per decision, an evaluator scores each, the best one wins. Applied separately to bidding, speaking, voting, and night actions. |

<table>
<tr>
<td align="center"><b>Baseline</b><br><a href="diagrams/baseline.png"><img src="diagrams/baseline.png" width="200"></a></td>
<td align="center"><b>Reflection</b><br><a href="diagrams/reflection.png"><img src="diagrams/reflection.png" width="200"></a></td>
<td align="center"><b>ReAct</b><br><a href="diagrams/react.png"><img src="diagrams/react.png" width="200"></a></td>
<td align="center"><b>Tree of Thoughts</b><br><a href="diagrams/ToT.png"><img src="diagrams/ToT.png" width="200"></a></td>
</tr>
</table>

<sub>Click any diagram to view it full size. Tree of Thoughts branches out this much for every single decision, bid, speech, vote, and night action alike, which is exactly why it costs 3.8x more LLM calls than Baseline.</sub>

<details>
<summary>See the full system architecture (game engine, tournament runner, and all four agents together)</summary>

![Full system architecture: game engine, tournament runner, and all four agent patterns in one diagram](diagrams/architecture_full.png)

</details>

## Game engine

8 players (2 werewolves, 1 seer, 1 doctor, 4 villagers). Each round: a night phase (werewolf kill, seer investigation, doctor protection), then a day phase (bid-based speaking order, adapted from Werewolf Arena's turn-taking design (Bailis et al., 2024), two rounds of discussion, a vote, an elimination). The rest of the environment design follows Xu et al. (ICML 2024), the methodology follows Wang et al. (ACL Findings 2024).

![Game engine flow: night phase, day phase (bidding, discussion, voting, elimination), and win-condition check](diagrams/game_engine.png)

## Tournament design

A mixed arena: all 8 agent types share the table, in a combinatorial design balanced so each role gets played equally often. That works out to `C(8,2) x C(6,1) x C(5,1) = 840` unique role assignments for a fully balanced run.

**Metrics:** win rate by role, werewolf detection accuracy, average survival round, vote alignment, false accusation rate, role prediction F1 score.

## How the design evolved

Adapting four different reasoning patterns to the same environment wasn't a one-time setup, the adaptation itself kept changing as the implementation matured. The four agent architectures weren't the only thing changing between games; the game itself kept getting richer as the engine matured. The clearest evidence is in the prompts themselves: for the same call type (a Tree of Thoughts voting decision), the prompt carried 781 tokens of game-state context in an early game and 3,296 tokens in a later one, over four times as much history, speech, and derived state feeding into the same decision point.

Play quality changed along with it. In game 14, Carol (a werewolf, playing the Reflection pattern) spent several rounds steadily building a case against an innocent player, Frank: "his reluctance to name specific suspects and his passive contributions raise serious concerns," "it's clear that he has evaded scrutiny while the rest of us are actively engaging." Frank was voted out. When suspicion then turned toward Carol herself, she reused the exact same move in reverse, against her own accuser: "his eagerness to direct suspicion towards me feels suspicious... could this be a tactic to deflect attention from himself?" Recognizing that you've become the target and reflexively turning your own successful tactic back on the accuser is coherent, multi-round deception that would take a reasonably sharp human player to counter.

## Why this stops at 14 games

14 games have been played, a small slice of the full 840-game balanced design, and that is where the project stops. Two reasons. First, the prompt structure, the tool set, and how much game history each agent sees all changed meaningfully while the four patterns were being adapted to the environment (see above), so games played under an earlier version of that setup aren't directly comparable to later ones anyway. Second, and more decisive: even with the adaptation settled, a statistically meaningful comparison needs on the order of hundreds of games per architecture, and cost scales badly here, total tokens per game grew from under 100,000 in game 1 to over 1.1 million in game 13. Scaling up by another order of magnitude, on top of a role-assignment issue in the scheduler that would need fixing first (every werewolf played so far has been Baseline or Reflection, never ReAct or ToT, see `docs/game_log_observations.md`), wasn't worth the cost for what this project set out to check. The results below are a directional first look, not a finished comparison, and the project stops there by choice rather than running out of runway.

## Results so far

14 games played across all four patterns. Werewolves won 10 of them (71%), roughly in line with findings elsewhere in the LLM social deduction literature.

On cost: Tree of Thoughts uses about 3.8x more LLM calls than Baseline per game (59.0 versus 15.6 on average), and Reflection isn't far behind ToT in call volume (56.0 on average) despite being conceptually simpler. ReAct adds latency beyond what its call count alone would suggest, since each tool round-trip costs extra time (about 65 seconds versus 33 for Baseline, averaged per game).

A full pass over all 14 games' logs, beyond the Carol example above, is in [`docs/game_log_observations.md`](docs/game_log_observations.md). It includes the scheduling issue mentioned above, a couple of qualitative claims about this dataset (a seer reveal being trusted, vote reasons being more candid than public speeches) that an earlier draft of this README made but that don't actually hold up against the logs, and a few smaller engineering notes (format-recovery events, a false alarm about corrupted text that turned out to be a display artifact, not a real bug).

## Repository structure

```
werewolf-work/
├── game/          Game engine: state, engine, LLM abstraction layer
├── agents/         The 4 agent architectures (baseline, reflection, react, tot)
├── tournament/      Tournament runner, scheduler, logging
├── logs/           Game logs (JSON/JSONL), traces, session summaries
├── scripts/
│   ├── run/          Entry points to play games (run_one.py, run_test.py, run_tournament.py)
│   ├── analysis/      Post-hoc analysis (analyze.py, analyze_tokens.py, analyze_speech_order.py, show_game.py)
│   └── tests/         LLM backend connection checks (Bedrock, local LM Studio)
├── diagrams/         Architecture and per-pattern flow diagrams
├── docs/            Literature review, and a full pass over the game logs
└── dashboard.py      Flask dashboard for browsing games, timelines, and API traces
```

## Tools

Python, LiteLLM (multi-provider LLM abstraction), the OpenAI SDK, AWS Bedrock (boto3), local LLM support via LM Studio, Flask, tiktoken for token counting.

## Academic references

- Wang et al., *"Boosting LLM Agents with Recursive Contemplation for Effective Deception Handling"*, ACL Findings 2024
- Xu et al., *"Language Agents with Reinforcement Learning for Strategic Play in the Werewolf Game"*, ICML 2024
- Bailis, Friedhoff, Chen, *"Werewolf Arena: A Case Study in LLM Evaluation via Social Deduction"*, arXiv:2407.13943
- Park et al., *"Generative Agents: Interactive Simulacra of Human Behavior"*, UIST 2023
- Arya et al., *"Revac: A Social Deduction Reasoning Agent"*, arXiv:2604.19523 (1st place, NeurIPS 2025 MindGames)

For the full literature review and reasoning, see [`docs/Wolfwere_Literature_Review.md`](docs/Wolfwere_Literature_Review.md).
