# Werewolf Agentic Arena

<details>
<summary>🇹🇷 Türkçe özet için tıklayın</summary>

**Araştırma sorusu:** LLM'in kendisinden bağımsız olarak, üzerine kurulan agentic akıl yürütme mimarisinin seçimi, bir sosyal çıkarım (social deduction) oyunundaki performansı ölçülebilir şekilde etkiliyor mu? Tüm ajanlar aynı LLM'i kullanıyor, tek değişken o LLM'in üzerine uygulanan agentic tasarım deseni.

**Literatürdeki boşluk:** mevcut çalışmalar ya farklı LLM'leri aynı mimaride karşılaştırıyor ya da yeni bir mimariyi 2-3 sabit baseline'a karşı test ediyor. Aynı LLM üzerinde, aynı Werewolf ortamında, standart agentic mimarilerin (Baseline/Reflection/ReAct/Tree-of-Thoughts) kontrollü bir taramasını yapan yayımlanmış bir çalışma yok, bu proje bu boşluğu dolduruyor.

**4 mimari karşılaştırılıyor:** Baseline (doğrudan prompt → aksiyon, kontrol grubu), Reflection (bir generator taslak üretir, bir critic tutarlılık/rol güvenliği/ikna ediciliğini değerlendirip gerekirse yeniden dener), ReAct (düşün → oyun durumu araçlarını sorgula → gözlemle → tekrar düşün → uygula), Tree of Thoughts (generator N aksiyon dalı üretir, bir simulator her dalı hayatta kalma olasılığına göre puanlar, bir evaluator en iyisini seçer).

**Oyun kurulumu:** 8 oyuncu (2 Kurt Adam, 1 Kahin, 1 Doktor, 4 Köylü), gece/gündüz fazları, çoğunluk oyuyla eleme.

**Turnuva tasarımı:** 8 ajan tipinin her rolü eşit sıklıkla oynayacağı dengelenmiş bir kombinatorik tasarım, 840 benzersiz rol ataması.

</details>

**Research question:** independent of the underlying LLM, does the choice of agentic reasoning architecture built on top of it measurably affect performance in a social deduction game? Every agent uses the same LLM. The only variable is the agentic design pattern applied to that LLM.

## The gap in the literature

Existing work either compares different LLMs on the same architecture, or tests one new architecture against two or three fixed baselines. Nobody had published a controlled sweep of standard agentic architectures (Baseline, Reflection, ReAct, Tree of Thoughts) on the same LLM in the same Werewolf environment. This project fills that gap.

## Four architectures compared

| Pattern | Mechanism |
|---|---|
| **Baseline** | Direct prompt to action. The control group. |
| **Reflection** | A generator LLM drafts an action, a critic LLM evaluates it for consistency, role safety, and persuasiveness, and retries if needed. |
| **ReAct** | Think, query the game-state tools (vote history, conversation log, survivors, suspicion graph, elimination history), observe, think again, act. |
| **Tree of Thoughts** | A generator produces N action branches, a simulator scores each on survival probability and suspicion, an evaluator picks the best one. |

## Game setup

8 players (2 werewolves, 1 seer, 1 doctor, 4 villagers), night and day phases, elimination by majority vote. The environment design follows Xu et al. (ICML 2024), the methodology follows Wang et al. (ACL Findings 2024).

## Tournament design

A mixed arena: all 8 agent types share the table, in a combinatorial design balanced so each role gets played equally often. That works out to `C(8,2) x C(6,1) x C(5,1) = 840` unique role assignments (1680 games recommended for statistical robustness).

**Metrics:** win rate by role, werewolf detection accuracy, average survival round, vote alignment, false accusation rate, role prediction F1 score.

## Architecture

```
game/         Game engine: state, engine, LLM abstraction layer
agents/       The 4 agent architectures (baseline, reflection, react, tot)
tournament/   Tournament runner, scheduler, logging
logs/         Game logs (JSON/JSONL), traces, session summaries
analyze*.py   Token usage, speech order, and results analysis
dashboard.py  Dashboard for visualizing games
```

## Tools

Python, LiteLLM (multi-provider LLM abstraction), the OpenAI SDK, AWS Bedrock (boto3), local LLM support via LM Studio, Flask, tiktoken for token counting.

## Academic references

- Wang et al., *"Boosting LLM Agents with Recursive Contemplation for Effective Deception Handling"*, ACL Findings 2024
- Xu et al., *"Language Agents with Reinforcement Learning for Strategic Play in the Werewolf Game"*, ICML 2024
- Bailis, Friedhoff, Chen, *"Werewolf Arena: A Case Study in LLM Evaluation via Social Deduction"*, arXiv:2407.13943
- Park et al., *"Generative Agents: Interactive Simulacra of Human Behavior"*, UIST 2023
- Arya et al., *"Revac: A Social Deduction Reasoning Agent"*, arXiv:2604.19523 (1st place, NeurIPS 2025 MindGames)

For the full literature review and reasoning, see `Wolfwere_Literature_Review.md`.
