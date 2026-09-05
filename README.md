# Werewolf Agentic Arena

**Araştırma sorusu:** LLM'in kendisinden bağımsız olarak, üzerine kurulan agentic akıl yürütme mimarisinin seçimi, bir sosyal çıkarım (social deduction) oyunundaki performansı ölçülebilir şekilde etkiliyor mu?

Tüm ajanlar **aynı LLM'i** kullanıyor — tek değişken, o LLM'in üzerine uygulanan agentic tasarım deseni.

## Literatürdeki Boşluk

Mevcut çalışmalar ya farklı LLM'leri aynı mimaride karşılaştırıyor (Werewolf Arena, Bailis et al. 2024) ya da yeni bir mimariyi 2-3 sabit baseline'a karşı test ediyor (Xu et al. ICML 2024, Wang et al. ACL 2024). **Aynı LLM üzerinde, aynı Werewolf ortamında, standart agentic mimarilerin (Baseline/Reflection/ReAct/Tree-of-Thoughts) kontrollü bir taramasını yapan yayımlanmış bir çalışma yok** — bu proje bu boşluğu dolduruyor.

## Karşılaştırılan 4 Mimari

| Desen | Mekanizma |
|---|---|
| **Baseline** | Doğrudan prompt → aksiyon. Kontrol grubu. |
| **Reflection** | Generator LLM taslak aksiyon üretir; Critic LLM tutarlılık/rol güvenliği/ikna ediciliği değerlendirir, gerekirse yeniden dener. |
| **ReAct** | Düşün → oyun durumu araçlarını sorgula (oy geçmişi, konuşma kaydı, hayatta kalanlar, şüphe grafiği, eleme geçmişi) → gözlemle → tekrar düşün → uygula. |
| **Tree of Thoughts** | Generator N aksiyon dalı üretir; Simulator LLM her dalı hayatta kalma olasılığı/şüphe skoruna göre puanlar; Evaluator en iyisini seçer. |

## Oyun Kurulumu

8 oyuncu (2 Kurt Adam, 1 Kahin, 1 Doktor, 4 Köylü), gece/gündüz fazları, çoğunluk oyuyla eleme. Ortam tasarımı Xu et al. (ICML 2024), metodoloji Wang et al. (ACL Findings 2024) referans alınarak kuruldu.

## Turnuva Tasarımı

Karma arena — 8 ajan tipi aynı masada, her rolü eşit sıklıkla oynayacak şekilde dengelenmiş kombinatorik tasarım: `C(8,2) × C(6,1) × C(5,1) = 840` benzersiz rol ataması (istatistiksel sağlamlık için önerilen: 1680 oyun).

**Ölçütler:** rol bazlı kazanma oranı, kurt adam tespit doğruluğu, ortalama hayatta kalma turu, oy hizalanması, yanlış suçlama oranı, rol tahmin F1 skoru.

## Mimari

```
game/        # Oyun motoru (state, engine, LLM soyutlama katmanı)
agents/      # 4 ajan mimarisi (baseline, reflection, react, tot)
tournament/  # Turnuva çalıştırıcı, zamanlayıcı, loglama
logs/        # Oyun kayıtları (JSON/JSONL), izler (traces), oturum özetleri
analyze*.py  # Token kullanımı, konuşma sırası, sonuç analizleri
dashboard.py # Oyunları görselleştiren dashboard
```

## Kullanılan Araçlar

Python — LiteLLM (çoklu LLM sağlayıcı soyutlaması), OpenAI SDK, AWS Bedrock (boto3), yerel LLM desteği (LM Studio), Flask, tiktoken (token sayımı).

## Akademik Referanslar

- Wang et al., *"Boosting LLM Agents with Recursive Contemplation for Effective Deception Handling"*, ACL Findings 2024
- Xu et al., *"Language Agents with Reinforcement Learning for Strategic Play in the Werewolf Game"*, ICML 2024
- Bailis, Friedhoff, Chen, *"Werewolf Arena: A Case Study in LLM Evaluation via Social Deduction"*, arXiv:2407.13943
- Park et al., *"Generative Agents: Interactive Simulacra of Human Behavior"*, UIST 2023
- Arya et al., *"Revac: A Social Deduction Reasoning Agent"*, arXiv:2604.19523 (NeurIPS 2025 MindGames 1. sıra)

Tam literatür taraması ve gerekçelendirme için `analysis.md` ve `Wolfwere_Literature_Review.md`.
