# Werewolf Agentic Arena

<details>
<summary>🇹🇷 Türkçe özet için tıklayın</summary>

**Amaç:** Werewolf (Mafia) oyununun, farklı agentic akıl yürütme mimarilerini (LLM'in kendisinden bağımsız olarak) karşılaştırmak için uygun bir benchmark ortamı olup olmadığını araştırmak. Oyun; gizli bilgi, aldatma, koalisyon kurma ve çok turlu uzun vadeli akıl yürütme gerektiriyor, tam olarak mimarileri birbirinden ayıran türde özellikler.

**4 mimari karşılaştırılıyor:** Baseline (kontrol grubu), Reflection (taslak → eleştiri → yeniden dene), ReAct (düşün → oyun durumu araçlarını sorgula → uygula), Tree of Thoughts (çoklu dal üretimi + değerlendirici seçimi).

**Tasarım süreç içinde gelişti:** Oyun durumu temsili (bağlam zenginliği) geliştikçe, oyuncu kalitesi de değişti. Aynı çağrı türü için (ToT oy stratejisi) prompt uzunluğu erken oyunlarda 781 token iken geç oyunlarda 3296 tokene çıktı. Somut bir örnek: geç bir oyunda Reflection deseniyle oynayan bir kurt adam (Carol), önce masum bir oyuncuyu ustaca hedef gösterip elettirdi, kendisi şüphelenilince aynı retorik hamleyi tam tersine çevirip şüphelenen kişiye karşı kullandı; çok turlu, tutarlı bir blöf.

**Durum: proje hâlâ devam ediyor.** Şu ana kadar 14 oyun oynandı (840 oyunluk dengeli tasarımın tamamı değil), bu bilinçli bir tercih: oyun tasarımı (prompt yapısı, araç seti, bağlam zenginliği) oturmadan önce büyük ölçekte oyun oynatmak, istatistiksel karşılaştırmayı anlamsız hale getirir. Mevcut 14 oyundan: Kurt Adamlar %71.4 kazandı (10/14), ToT bir oyunda Baseline'a göre ortalama ~3.8× daha fazla LLM çağrısı kullanıyor.

</details>

---

This project explores whether Werewolf (Mafia) is a good benchmark for comparing agentic reasoning architectures, independent of which LLM sits underneath them. Every agent in every game uses the same LLM; the only variable is the agentic design pattern applied to it.

## Why Werewolf as a benchmark

Most agentic-architecture comparisons either test different LLMs on one fixed architecture, or pit one new architecture against two or three ad hoc baselines. There's no controlled, published sweep of standard agentic patterns (Baseline, Reflection, ReAct, Tree of Thoughts) run on the same LLM in the same environment. Werewolf is a strong candidate for that kind of benchmark: it demands private information, deception, coalition-building, and reasoning that compounds across multiple rounds, the exact properties that separate reasoning architectures from each other far more sharply than a single-turn QA benchmark would. This project builds that benchmark environment and runs the first sweep through it.

## Four architectures compared

| Pattern | Mechanism |
|---|---|
| **Baseline** | Direct prompt to action. The control group. |
| **Reflection** | A generator LLM drafts an action, a critic LLM evaluates it for consistency, role safety, and persuasiveness, and retries if needed. |
| **ReAct** | Think, query the game-state tools (vote history, conversation log, survivors, suspicion graph, elimination history), observe, think again, act. |
| **Tree of Thoughts** | A generator produces multiple parallel branches per decision, an evaluator scores each, the best one wins. Applied separately to bidding, speaking, voting, and night actions. |

![Tree of Thoughts branching structure across all four game actions](diagrams/ToT.png)

## Game engine

8 players (2 werewolves, 1 seer, 1 doctor, 4 villagers). Each round: a night phase (werewolf kill, seer investigation, doctor protection), then a day phase (bid-based speaking order, two rounds of discussion, a vote, an elimination). The environment design follows Xu et al. (ICML 2024), the methodology follows Wang et al. (ACL Findings 2024).

![Game engine flow: night phase, day phase (bidding, discussion, voting, elimination), and win-condition check](diagrams/game_engine.png)

## Tournament design

A mixed arena: all 8 agent types share the table, in a combinatorial design balanced so each role gets played equally often. That works out to `C(8,2) x C(6,1) x C(5,1) = 840` unique role assignments for a fully balanced run.

**Metrics:** win rate by role, werewolf detection accuracy, average survival round, vote alignment, false accusation rate, role prediction F1 score.

## How the design evolved

The four agent architectures weren't the only thing changing between games; the game itself kept getting richer as the engine matured. The clearest evidence is in the prompts themselves: for the same call type (a Tree of Thoughts voting decision), the prompt carried 781 tokens of game-state context in an early game and 3,296 tokens in a later one, over four times as much history, speech, and derived state feeding into the same decision point.

Play quality changed along with it. In game 14, Carol (a werewolf, playing the Reflection pattern) spent several rounds steadily building a case against an innocent player, Frank: "his reluctance to name specific suspects and his passive contributions raise serious concerns," "it's clear that he has evaded scrutiny while the rest of us are actively engaging." Frank was voted out. When suspicion then turned toward Carol herself, she reused the exact same move in reverse, against her own accuser: "his eagerness to direct suspicion towards me feels suspicious... could this be a tactic to deflect attention from himself?" Recognizing that you've become the target and reflexively turning your own successful tactic back on the accuser is coherent, multi-round deception that would take a reasonably sharp human player to counter.

## Status: still in progress

14 games have been played so far, not the full 840-game balanced design. That's intentional. The prompt structure, the tool set, and how much game history each agent sees have all kept changing meaningfully between sessions, exactly the evolution described above, so pooling every game played so far into one statistical comparison would mix data from meaningfully different versions of the game. The results below are a directional first look, not a finished comparison. The next phase is to freeze the current design and run enough games under it for the per-architecture differences to be statistically meaningful rather than merely suggestive.

## Results so far

14 games played across all four patterns. Werewolves won 10 of them (71%), roughly in line with findings elsewhere in the LLM social deduction literature.

On cost: Tree of Thoughts uses about 3.8x more LLM calls than Baseline per game (59.0 versus 15.6 on average), and Reflection isn't far behind ToT in call volume (56.0 on average) despite being conceptually simpler. ReAct adds latency beyond what its call count alone would suggest, since each tool round-trip costs extra time (about 65 seconds versus 33 for Baseline, averaged per game).

A few qualitative observations stood out beyond the Carol example above: Seer information sharing worked as intended when the Seer chose to reveal, and vote justifications (recorded but not shown to other players) were consistently more candid than the public speeches, which is exactly the kind of signal this environment is designed to surface.

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
├── docs/            Literature review
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
