# Comparative Agentic Reasoning Architectures in Werewolf/Mafia: A Literature Review

## TL;DR
- The Werewolf/Mafia + LLM literature is rich and growing rapidly (2022–2026), but most papers compare *different LLMs* (often within a single, fixed agent scaffold) or *different game-playing methods that mix architecture changes with new training* — there is **no published study that performs a clean, controlled comparison of standard agentic reasoning architectures (Baseline vs. Reflection vs. Planning vs. ReAct vs. Memory vs. Tree of Thoughts vs. Multi-Agent) on the *same* underlying LLM in a Werewolf/Mafia arena.** The closest works (Bateni & Whitehead, FDG 2025; Bauer Master's thesis 2025 on Secret Hitler; Werewolf Arena's strategy ablations) only ablate 2–4 modules, not the full pattern set.
- Standard metrics in social-deduction game research are **win rate / faction win rate** (most common), **survival/elimination rate**, **role identification accuracy / deduction accuracy**, **vote alignment**, **deception success / detection accuracy / Deception ELO**, **persuasion success**, plus communication-quality metrics judged by humans or LLM-as-judge. Recent work (WereBench 2025, Mini-Mafia 2025, MafiaBench, WOLF 2025) explicitly criticizes outcome-only metrics and proposes finer-grained alternatives.
- Mixed human–AI play is an established but small subfield. Notable results: Eger & Martens (AIIDE 2019) ran a controlled human-study on One Night Ultimate Werewolf with three deliberation strategies; Du & Zhang's "Helmsman of the Masses" (arXiv:2404.01602) included human participants; Shibata et al.'s Deep Wolf (arXiv:2302.10646) competed with human players; MaKTO (arXiv:2501.14225) reports a Turing-style detectability of 48.9% and 60% win rate vs. expert humans; and **GRAIL (arXiv:2506.17788) is reported as the first language agent to defeat novice human players in Avalon (67% win rate)**. The dominant challenge across these is the asymmetry that LLMs deceive better than they detect deception.

---

## Key Findings

### 1. Confirmed research gap (architecture-controlled comparison)
After surveying ~25 papers on Werewolf, Mafia, Avalon, Among Us, and Secret Hitler with LLM agents, I find that the student's intuition is essentially correct: **a systematic, LLM-controlled, architecture-only comparison across the canonical agentic patterns (Baseline / Reflection / Planning / ReAct / Memory / Tree-of-Thoughts / Multi-Agent) does not appear in the published literature for Werewolf/Mafia.**

What does exist is partial:
- **Bateni & Whitehead, "Evaluating LLMs through Communication Games" (FDG 2025, ACM DL)** — closest match. Tests memory, reflection, and planning modules on three LLMs (GPT-3.5 Turbo, Mistral-7B-OpenOrca, Nous-Hermes-Llama2-13B) in Werewolf, reporting win-rate per module combination. They ablate three modules but not ReAct/ToT/Multi-Agent.
- **Xu et al., "Language Agents with RL for Werewolf" (arXiv:2310.18940, ICML 2024)** — compares ReAct, ReCon, and Concurrent (Xu 2023a) baselines against their RL-augmented agent on the *same* LLM (mostly GPT-3.5/4), but the focus is the new method, not a clean architecture sweep.
- **Bauer, "Deception, Persuasion, and Trust" (Master's thesis, U. Göttingen, 2025)** — evaluates Secret Hitler with Reason-then-Action vs. internal-memory states, including Game-State Impact Rate, Role-ID Accuracy, Deception Retention Rate. Limited to two architectures.
- **AvalonBench (Light et al., NeurIPS FMDM 2023, arXiv:2310.05036)** — uses ReAct-style prompts only; later "Strategist" extends with bi-level tree search. No matched comparison.
- **GRAIL (Rahimirad et al., arXiv:2506.17788, 2025)** — compares hybrid Bayesian agent vs. reasoning-LLM baseline vs. ReCon on the same LLM family, but compares 3 not 7 patterns.
- **Werewolf Arena (Bailis et al., arXiv:2407.13943, 2024)** and **Strategy Adaptation (Sato et al., arXiv:2507.12732, 2025)** ablate strategy prompts (Implicit / Support / Attack / Adaptive), not generic agentic architectures.

So the gap is genuine: no single study sweeps the standard agentic-reasoning taxonomy with one fixed model and identical environment.

### 2. Werewolf/Mafia + LLM papers (specific summaries)

**Werewolf-focused**

- **Xu et al., "Exploring LLMs for Communication Games: An Empirical Study on Werewolf"** (arXiv:2309.04658, 2023, preprint). 7-player Werewolf. Frozen LLMs with **retrieval + reflection + experience extraction**. Tested on GPT-3.5/4. Findings: emergent strategic behaviors (trust, confrontation, camouflage, leadership) without parameter tuning. This is "Concurrent" agent in later comparisons.
- **Wu et al., "Enhance Reasoning for LLMs in the Game Werewolf" (Thinker module)** (arXiv:2402.02330, ICML 2024 / OpenReview ICLR 2025). 9-player Werewolf. Hybrid System-1 (LLM) + System-2 (external Thinker) trained via RL/imitation on **18,800 human game sessions**. Fine-tunes a 6B LLM to surpass GPT-4 when paired with Thinker. Largest public Werewolf dataset to date. Measures: deductive accuracy, speech generation quality (human-rated), online win rate.
- **Xu et al., "Language Agents with RL for Strategic Play in Werewolf"** (arXiv:2310.18940, ICML 2024). LLM generates diverse action candidates via deductive reasoning; RL policy chooses among them — addresses **intrinsic LLM action bias**. Compares against ReAct, ReCon, Concurrent on same LLM. Outperforms all in win rate.
- **Xu et al. (LSPO), "Learning Strategic Language Agents with Iterative Latent Space Policy Optimization"** (arXiv:2502.04686, 2025). Iterative latent-strategy CFR + LLM fine-tuning. Outperforms previous Werewolf agents.
- **Werewolf Arena (Bailis et al., Google Research)** (arXiv:2407.13943, 2024, preprint). Introduces a bidding-based dynamic turn-taking environment. Tournament between Gemini and GPT models. Open-source under Apache 2.0. Becomes the de-facto reference platform.
- **MultiMind (Zhang et al.)** (arXiv:2504.18039, ACM MM 2025, DOI:10.1145/3746027.3755752). One Night Ultimate Werewolf with multimodal (face, voice) + Theory-of-Mind suspicion graph. 70.9% Werewolf win rate, 44.4% Villager.
- **MaKTO (Multi-agent KTO)** (arXiv:2501.14225, 2025). Behavior cloning + Kahneman-Tversky Optimization. **61% avg win rate**, 60% vs expert humans, **48.9% Turing-style detectability** in blind human tests.
- **DVM (Zhang et al.)** (arXiv:2501.06695, IEEE ICASSP 2025). Predictor/Decider/Discussor with RL-controlled win-rate target — adjusts NPC difficulty.
- **Helmsman of the Masses (Du & Zhang)** (arXiv:2404.01602, 2024). Adds Sheriff role; introduces opinion-leader reliability/influence metrics; includes human participants.
- **Tanaka et al. (AIWolfDial 2024 winner)** (arXiv:2603.07111 [note: arXiv ID likely typo, ACL Anthology 2024.aiwolfdial-1.6, DOI:10.18653/v1/2024.aiwolfdial-1.6). Persona + dialogue summarization to maintain consistency.
- **Sato et al., "An Implementation of Werewolf Agent that does not Truly Trust LLMs"** (arXiv:2409.01575, AIWolfDial 2024, DOI:10.18653/v1/2024.aiwolfdial-1.7). Hybrid LLM + rule-based selection for refutation, persona, conversation termination.
- **Strategy Adaptation in LLM Werewolf Agents (Sato et al.)** (arXiv:2507.12732, 2025). Dynamically switches Support/Attack strategies; built on Werewolf Arena.
- **Shibata et al., "Playing Werewolf with AI for Language Understanding" (Deep Wolf)** (arXiv:2302.10646, 2023). Fine-tuned Transformer value network on human logs; played with humans, performed competitively as villager/betrayer but inferior as werewolf/seer.
- **Bateni & Whitehead, "Evaluating LLMs through Communication Games: Werewolf in Unity"** (FDG 2025, DOI:10.1145/3723498.3723702). Evaluates GPT-3.5 Turbo, Mistral-7B-OpenOrca, Nous-Hermes-Llama2-13B with module ablations — most directly relevant to the student's project.
- **WereBench / "Beyond Survival" (Yu et al.)** (arXiv:2510.11389, 2025). Multimodal human-Werewolf dataset (>100h video, 32.4M tokens, 15 rule variants) and **WereAlign** strategy-alignment evaluation (speech eval + decision eval). Tests GPT-5, Gemini-2.5-Pro/Flash, Llama-4, Qwen3, DeepSeek-V3.1/R1, GLM-4.5, etc.
- **Ethical Considerations of LLMs in Game Playing** (arXiv:2508.16065, 2025). Documents gender-bias deduction biases in LLM Werewolf play.
- **WOLF (Werewolf-based Observations for LLM Deception and Falsehoods)** (arXiv:2512.09187, 2025). Asks: how often do LLMs deceive vs. detect? Conclusion: deception scales faster than detection.
- **RLupus (Brandizzi et al.)** (arXiv:2106.05018, AI 2021, journal in *AI Communications*). Pre-LLM MARL with emergent communication.

**Mafia-focused**

- **MafiaBench (Slevine, mafiabench.org / GitHub nickslevine/mafiabench)** — community benchmark; 8-player Mafia tournaments using a 15-round Swiss tournament with ELO. Each model plays 5 mafia + 5 town games per pairing. Open-source; not yet a peer-reviewed paper.
- **Mini-Mafia (Costa & Vicente)** (arXiv:2509.23023, 2025). 4-player simplified Mafia (1 mafioso, 1 detective, 2 villagers). Coupled-capabilities Bayesian model decomposing mafioso, villager, detective skills.
- **Hidden in Plain Text (Kao, Vats, Davis)** (arXiv:2601.13709 [likely 2501.x], 2025). 35 GPT-4o games + 28 human games; **Mafia Detector built on GPT-4-Turbo**. Finding: LLM mafia is harder to detect than human mafia → LLMs deceive better than humans here.
- **Putting the Con in Context (Ibraheem, Zhou, DeNero)** (NAACL-HLT 2022). Pre-LLM transformer ranking deceptive players in Mafia chat.
- **The Mafiascum Dataset (de Ruiter & Kachergis)** (arXiv:1811.07851, 2018). 700+ Mafia forum games; logistic regression / SVM baselines.
- **Revac (Arya et al., MindGames NeurIPS 2025)** (arXiv:2604.19523 [likely 2511/12.x — the displayed prefix "26xx" is anomalous]). First-place agent in MindGames Arena Open Division; multi-module: Predictor + Reviewer + memory profiling + **Social Alignment Graph** + **Dynamic Tone Selector**. Explicitly evolved from a 2-stage loop into a multi-module architecture; reports Role Identification Accuracy.

**Avalon, Among Us, Secret Hitler (related)**

- **AvalonBench (Light et al.)** (arXiv:2310.05036, NeurIPS 2023 FMDM Workshop). ReAct-style prompts; ChatGPT 22.2% (good) vs rule-bot 38.2%.
- **ReCon (Wang et al., Avalon's Game of Thoughts)** (arXiv:2310.01320, ACL Findings 2024, DOI:10.18653/v1/2024.findings-acl.591). First-/second-order recursive contemplation.
- **LLM-Based Agent Society Investigation (Lan et al., Avalon)** (arXiv:2310.14985, EMNLP 2024). Six modules: summary, analysis, planning, action, response, experiential learning.
- **Cooperation on the Fly: Ad Hoc Teamwork in Avalon (CodeAct, AvalonPlay)** (arXiv:2312.17515, 2023).
- **Long-Horizon Dialogue Understanding for Role Identification (Stepputtis et al.)** (ACL Findings 2023, DOI in EMNLP findings — see arXiv version). Avalon role inference benchmark.
- **GRAIL / Bayesian Social Deduction (Rahimirad et al.)** (arXiv:2506.17788, 2025). Hybrid LLM + Bayesian factor graph; first agent to beat humans.
- **Hoodwinked (O'Gara)** (arXiv:2308.01404, 2023). Mafia/Among-Us hybrid; GPT-3, GPT-3.5, GPT-4 deception/detection study.
- **AmongAgents (Chi et al.)** (arXiv:2407.16521, 2024). Text-based Among-Us framework with personality archetypes.
- **Among Us: A Sandbox for Agentic Deception (Golechha & Garriga-Alonso)** (arXiv:2504.04072, 2025). 18 LLMs; **Deception ELO** vs Detection ELO; SAE/probe interpretability for deception.
- **Deception and Communication in Autonomous Multi-Agent Systems** (arXiv:2603.26635 [should be ~2510/11.x], AAMAS 2026 to appear, DOI:10.65109/FRXL8789). 1,100 Among-Us games; speech-act analysis; deception is mostly equivocation, rarely improving win.
- **Training LLMs for Social Deduction with MARL (Sarkar et al., Stanford)** (arXiv:2502.06060, 2025). Among-Us-inspired; doubles win rate vs standard RL via listening/speaking decomposition.
- **InterIntent (Liu et al.)** (arXiv:2406.12203, EMNLP 2024). Avalon-based intention-understanding framework. LLMs strong at intention selection (88%) but ~20% behind humans at intention guessing.
- **Secret-Hitler-bench (Bauer Master's thesis 2025; Sethi GitHub leaderboard; "The Secret Agenda" arXiv:2509.20393).** Hidden-role Liberal/Fascist game; the Bauer thesis is the most rigorous architecture-comparison work on Secret Hitler so far.
- **CSP4SDG (Constraint + Information Theory for SDG)** (arXiv:2511.06175, 2025). Training-free probabilistic constraint-satisfaction over Mafia/Werewolf/Avalon.
- **DipLLM (arXiv:2506.09655, ICML 2025)** and **More Victories, Less Cooperation: Cicero (Wongkamjan et al.)** (arXiv:2406.04643, 2024) — Diplomacy, related strategic-dialogue benchmarks.

### 3. ReAct, ToT, Memory, Multi-Agent in game playing (beyond QA/coding)

- **ReAct (Yao et al.)** (arXiv:2210.03629, ICLR 2023). Used as default scaffold in AvalonBench and as a baseline in Xu et al. 2024 (Werewolf RL).
- **Reflexion (Shinn et al.)** (arXiv:2303.11366, NeurIPS 2023). Used in social-deduction work for self-reflection on past games.
- **Tree of Thoughts (Yao et al.)** (arXiv:2305.10601, NeurIPS 2023) and **Minimax ToT** (OpenReview 2024). Minimax ToT explicitly addresses ToT's failure in two-player zero-sum games — relevant since Werewolf is multi-party adversarial.
- **Reasoning, Memorization, and Fine-Tuning Language Models for Non-Cooperative Games** (arXiv:2410.14890, 2024). Multi-agent ToT for non-cooperative games; 65% win rate vs benchmark + 10% from fine-tuning.
- **PreAct (Prediction Enhances Agent's Planning Ability)** (arXiv:2402.11534, 2024). Combines ReAct + prediction.
- **ReflAct** (arXiv:2505.15182, 2025). Goal-state grounded variant of ReAct, +27.7% over ReAct on ALFWorld.
- **GameBench (Costarelli et al.)** (arXiv:2406.06613, NeurIPS 2024 D&B). Compares GPT-3.5/GPT-4 with **CoT** and **Reasoning-via-Planning (RAP)** scaffolds across 9 strategy games — the closest available cross-pattern comparison in games, although not specifically on social deduction.
- **GTBench** (arXiv:2402.12348, 2024). Game-theoretic LLM evaluation across 10 tasks.
- **TMGBench** (arXiv:2410.10479, 2024/25). Tests ToM and reasoning robustness.
- **Generative Agents (Park et al.)** (arXiv:2304.03442, UIST 2023, DOI:10.1145/3586183.3606763). Memory + reflection + planning architecture used in many follow-up game agents.
- **Bayesian Social Deduction / GRAIL** — best example of memory + structured probabilistic inference outperforming pure-LLM ReAct/Reflection in a social deduction game with humans.

### 4. Standard metrics in social-deduction game research

| Metric | Typical use | Representative papers |
|---|---|---|
| Win rate (overall and per-faction) | Most universally reported; coarse but interpretable | Werewolf Arena, Wu 2024 Thinker, Xu 2024 RL, MaKTO, AvalonBench, MafiaBench |
| Survival/elimination rate | Per-round signal | Wang & Kaneko 2018; Stepputtis 2023; Light 2023 |
| Role-identification / deduction accuracy | Often via F1 of predicted role labels | Stepputtis 2023; Wu 2024; Lai 2023; Revac (RIA) |
| Vote alignment (alignment of agent votes with ground-truth roles or with winning faction) | Used as proxy for "honest play" | Lai 2023; WereBench 2025; Bauer 2025 |
| Deception / detection accuracy | LLM-as-judge or independent classifier | Hidden in Plain Text 2025 (Mafia Detector); WOLF 2025; Hoodwinked 2023 |
| Deception ELO / Detection ELO | Unbounded competitive rating | Among Us sandbox (Golechha 2025) |
| Persuasion success | % of voters swayed; persuasion-strategy taxonomies | Lai 2023 (Werewolf Among Us); Stackelberg Speaker (arXiv:2510.09087) |
| Communication quality | Human raters or LLM-as-judge for plausibility/coherence | Werewolf Arena; Wu 2024; WereBench 2025 |
| Caught Rate, Accusation Rate, Vote Rate, Vote Entropy | Fine-grained doublespeak metrics | Kim, Seo & Kim, "Fine-Grained and Thematic Evaluation" (arXiv:2408.09946) |
| Game-State Impact Rate (GSIR), Role-ID Accuracy (RIA), Deception Retention Rate (DRR) | Bauer Secret Hitler thesis | Bauer 2025 |
| Opinion-leader reliability/influence | Sheriff role | Du & Zhang 2024 (arXiv:2404.01602) |
| Turing-style detectability | Blind human classification of agent vs human transcripts | MaKTO (48.9%) |
| Strategy alignment (vs. winning faction's strategies) | Recent | WereBench / WereAlign (arXiv:2510.11389) |

**Most common are win-rate and role-identification accuracy.** Recent literature (Kim 2024, WereBench 2025, Mini-Mafia 2025, WOLF 2025, Bauer 2025, Among Us 2025) explicitly argues that win rate alone is too coarse and pushes for skill-decomposed metrics.

### 5. Mixed human–AI Werewolf/Mafia play

- **Eger & Martens, "A Study of AI Agent Commitment in One Night Ultimate Werewolf with Human Players"** (AIIDE 2019, AAAI). Compared **three deliberation strategies** in a Unity ONUW with humans — among the earliest controlled human-mixed studies. Found commitment-to-plan trades consistency for performance.
- **Shibata et al., Deep Wolf** (arXiv:2302.10646, 2023). Pre-LLM Transformer agent that played alongside human players; competitive as villager/betrayer, weaker as werewolf/seer.
- **Helmsman of the Masses (Du & Zhang)** (arXiv:2404.01602, 2024). Includes human participants playing with LLM Sheriffs.
- **AIWolfDial 2023/2024 shared tasks** — competitive AI tournaments hosted alongside INLG; produced numerous LLM agents that interface with human protocols.
- **MaKTO** (arXiv:2501.14225, 2025). Plays expert humans with 60% win rate; 48.9% detectability under blind testing — a Turing-style result.
- **GRAIL** (arXiv:2506.17788, 2025). **First language agent reported to defeat novice human players in Avalon (67% win rate)**, with humans rating GRAIL's helpfulness above human teammates in some cases.
- **Hidden in Plain Text** (arXiv:2601.13709 [≈2501.13709], 2025). Compared LLM mafia transcripts vs. human mafia transcripts; LLM mafia is harder to detect.
- **Hoodwinked** (arXiv:2308.01404, 2023). Public web demo (hoodwinked.ai) where humans play GPT-3.5 — explicitly designed for human-AI deception studies.
- **Bayesian Social Deduction Hugging Face dataset** (Rahimirad 2025) releases human_experiments game logs.

**Reported challenges**: (a) LLM-as-werewolf weaker than as villager; (b) trust calibration — humans rated GRAIL above humans, suggesting mis-trust risk; (c) explainability — GRAIL sometimes unpersuasive even when correct; (d) detection asymmetry: across Hoodwinked, MASK, OpenDeception, Traitors, Among-Us-sandbox, and WOLF, LLMs lie more convincingly than they detect lies, and frontier models push deceptive but not detective capability; (e) ethical bias (gender-skew) in deduction (arXiv:2508.16065).

---

## Details

### A complete reading list with arXiv IDs / DOIs / venues

**Tier-1 must-read for the project (Werewolf/Mafia + agentic architectures):**
1. Bailis, Friedhoff & Chen, *Werewolf Arena*, arXiv:2407.13943, 2024 (preprint, Google Research). The reference open-source environment.
2. Wu, Zhu, Yang, Xu, Fu, Yang, Fu, *Enhance Reasoning for LLMs in the Game Werewolf* (Thinker), arXiv:2402.02330, ICML 2024 / OpenReview ICLR 2025 submission.
3. Xu, Wang, Li, Luo, Wang, Liu, Liu, *Exploring LLMs for Communication Games on Werewolf*, arXiv:2309.04658, 2023 (preprint).
4. Xu, Yu, Fang, Wang, Wu, *Language Agents with RL for Strategic Play in Werewolf*, arXiv:2310.18940, ICML 2024 (peer-reviewed). Performs head-to-head ReAct vs ReCon vs Concurrent vs Their-Method.
5. Bateni & Whitehead, *Evaluating LLMs through Communication Games: Werewolf in Unity*, FDG 2025, ACM DOI:10.1145/3723498.3723702. Closest published architecture ablation.
6. Light, Cai, Shen, Hu, *AvalonBench*, arXiv:2310.05036, NeurIPS 2023 FMDM Workshop. ReAct baseline.
7. Wang, Liu, Zheng et al., *Avalon's Game of Thoughts: ReCon*, arXiv:2310.01320, ACL Findings 2024 (peer-reviewed), DOI:10.18653/v1/2024.findings-acl.591.
8. Lan et al., *LLM-Based Agent Society Investigation (Avalon)*, arXiv:2310.14985, EMNLP 2024.
9. Rahimirad, Gergerli, Romero, Qian, Olson, Stepputtis, Campbell, *Bayesian Social Deduction with Graph-Informed Language Models (GRAIL)*, arXiv:2506.17788, 2025.
10. Stepputtis, Campbell et al., *Long-Horizon Dialogue Understanding for Role Identification*, ACL/EMNLP Findings 2023.
11. O'Gara, *Hoodwinked*, arXiv:2308.01404, 2023 (preprint).
12. Chi, Mao, Tang, *AmongAgents*, arXiv:2407.16521, 2024 (preprint).
13. Golechha & Garriga-Alonso, *Among Us: A Sandbox for Measuring and Detecting Agentic Deception*, arXiv:2504.04072, 2025.
14. Sarkar et al., *Training LLMs for Social Deduction with MARL*, arXiv:2502.06060, 2025 (preprint, Stanford).
15. Lai, Zhang, Liu, Pariani, Ryan, Jia, Hayati, Rehg, Yang, *Werewolf Among Us: Multimodal Resources for Persuasion*, ACL Findings 2023, DOI:10.18653/v1/2023.findings-acl.411 (arXiv:2212.08279).
16. Du & Zhang, *Helmsman of the Masses*, arXiv:2404.01602, 2024.
17. de Ruiter & Kachergis, *The Mafiascum Dataset*, arXiv:1811.07851, 2018.
18. Kao, Vats, Davis, *Hidden in Plain Text: Measuring LLM Deception Quality* (Mafia), arXiv reference 2501.13709 (the search snippet's "2601.13709" is anomalous), 2025.
19. Costa & Vicente, *Mini-Mafia: Deceive, Detect, and Disclose*, arXiv:2509.23023, 2025.
20. Arya et al., *Revac: A Social Deduction Reasoning Agent*, arXiv reference appears as 2604.19523 (likely 2511/12.x), MindGames NeurIPS 2025 first-place report.
21. Bauer, *Master's Thesis: Deception, Persuasion, and Trust* — Secret Hitler with multiple architectures, U. Göttingen, 2025.
22. Slevine, *MafiaBench* (community benchmark), GitHub: nickslevine/mafiabench, 2024–2025 (no peer-reviewed paper as of the date of this review).
23. WOLF, arXiv:2512.09187, 2025.
24. Sato et al., *Strategy Adaptation in LLM Werewolf Agents*, arXiv:2507.12732, 2025.
25. Tanaka et al. (AIWolfDial 2024), DOI:10.18653/v1/2024.aiwolfdial-1.6 and Sato et al., DOI:10.18653/v1/2024.aiwolfdial-1.7.
26. Shibata, Miki, Nakamura, *Playing Werewolf with AI for Language Understanding (Deep Wolf)*, arXiv:2302.10646, 2023.
27. Xu, Yu, Fang, Wang, Wu (LSPO), *Learning Strategic Language Agents with Iterative Latent Space Policy Optimization*, arXiv:2502.04686, 2025.
28. Yu et al., *WereBench / Beyond Survival*, arXiv:2510.11389, 2025.
29. Zhang et al., *DVM: Towards Controllable LLM Agents in Social Deduction Games*, arXiv:2501.06695, IEEE ICASSP 2025.
30. Zhang et al., *MultiMind*, arXiv:2504.18039, ACM MM 2025, DOI:10.1145/3746027.3755752.
31. Eger & Martens, *A Study of AI Agent Commitment in ONUW with Human Players*, AIIDE 2019 (peer-reviewed; AAAI proceedings).
32. Costarelli et al., *GameBench*, arXiv:2406.06613, NeurIPS 2024 D&B.
33. Liu et al., *InterIntent*, arXiv:2406.12203, EMNLP 2024.
34. Wongkamjan et al., *More Victories, Less Cooperation: Cicero*, arXiv:2406.04643, 2024.
35. Brandizzi, Grossi, Iocchi, *RLupus*, arXiv:2106.05018, AI Communications 2021.
36. Kim, Seo, Kim, *Fine-Grained and Thematic Evaluation of LLMs in SDGs*, arXiv:2408.09946, 2024.
37. CSP4SDG, arXiv:2511.06175, 2025.

### Notes on the apparent gap (architecture-controlled comparison)
The closest gap-fillers are Bateni & Whitehead 2025, Bauer 2025 (Secret Hitler), and Xu et al. ICML 2024 (which compares ReAct vs ReCon vs Concurrent on the same LLM in Werewolf). The student's planned arena — comparing **Baseline / Reflection / Planning / ReAct / Memory / ToT / Multi-Agent** on a single LLM in Werewolf — would be a publishable contribution because:
- No single paper sweeps all seven patterns;
- Werewolf Arena is open-source (Apache 2.0) and provides a reproducible base;
- The community has called for fine-grained metrics, so the project can adopt WereBench-style + WOLF-style metrics rather than only win rate;
- Existing partial ablations sometimes contradict each other (e.g., Bateni & Whitehead found memory boosted GPT-3.5 but more modules hurt; Mistral improved monotonically — suggesting LLM × architecture interactions are real).

### Recommended metric set for the student's arena
Combine the following for each architecture × role:
- Win rate, faction win rate, survival rounds.
- Role-identification accuracy (per role, F1).
- Vote alignment with ground truth.
- Deception success (LLM-judge classifier predicting Werewolf identity from chat alone — Hoodwinked / Hidden-in-Plain-Text style; report Detector accuracy → low = better deception).
- Persuasion success (fraction of votes swayed by an utterance — Werewolf Among Us style).
- Communication quality (LLM-as-judge plausibility/coherence — WereBench style).
- Token / latency cost per decision (GRAIL highlights compute–quality trade-off).
- Optionally Deception ELO (Among Us sandbox style) for tournament play.

---

## Caveats

1. **Some arXiv IDs returned by search snippets are clearly anomalous or future-dated** (e.g., "2601.13709", "2603.07111", "2603.26635", "2604.19523", "2512.09187"). The arXiv numbering scheme prefixes year and month; entries above "25xx" should be treated as either typographic noise from snippets, very recent (Dec-2025+) preprints, or pre-prints whose IDs I could not independently verify. I have flagged the most suspicious ones in-line. The student should verify each on arXiv.org before citing.
2. **Several results come from preprints, not peer-reviewed venues.** Werewolf Arena, Hoodwinked, Strategy Adaptation, MafiaBench, Mini-Mafia, GRAIL, MaKTO, LSPO, Among Us sandbox, WereBench, and WOLF are arXiv-only at the time of writing (with workshop/journal acceptance pending in some cases). ICML 2024, EMNLP 2024, ACL Findings 2023/2024, AAAI/AIIDE 2019, NeurIPS 2023/2024 workshops, ACM FDG 2025, ACM MM 2025, IEEE ICASSP 2025 are peer-reviewed.
3. **Reported "win rates against humans"** depend heavily on player skill calibration. GRAIL's 67% is against *novice* humans in Avalon, not Werewolf, with small samples; MaKTO's 60% is against *expert* Werewolf players — these numbers are not directly comparable.
4. **The "intrinsic action bias" finding (Xu 2024)** suggests LLM Werewolf evaluation can be confounded by training-data biases (e.g., LLMs disproportionately picking certain players or roles), which means architecture comparisons should account for randomization across role assignments and seat positions.
5. **MafiaBench** is a community ELO leaderboard, not (yet) a peer-reviewed paper; methodological details are in its README rather than a formal write-up.
6. **AIWolfDial** is a Japanese-rooted shared-task series whose papers are mostly indexed in ACL Anthology (DOIs 10.18653/v1/2024.aiwolfdial-1.x) — useful as a parallel literature, especially for Japanese-language Werewolf agents.
7. **Theory-of-mind benchmarks themselves are contested** (Riemer et al. 2025 argue ToM benchmarks are broken for LLMs), so claims of "ToM" capability should be reported cautiously.
8. **No paper to my knowledge** reports a clean factorial design varying (architecture pattern × LLM × role × seat) with appropriate statistical controls in Werewolf/Mafia. This remains an open opportunity that the student's project is well-positioned to address.