# Evaluation results

Generated 2026-11-10 00:10 UTC by `python -m evals.run_evals`.

- Dataset: 30 answerable + 5 unanswerable questions over the 8 sample documents (English and German, see `evals/dataset.json`)
- LLM: `qwen3:8b` via ollama; embeddings: `nomic-embed-text` via ollama; judge: `qwen3:8b`
- Retrieval: top_k=5, candidate_k=20, RRF k=60, refusal threshold=0.25, re-ranking=off

## Retrieval quality (dense vs BM25 vs hybrid, chunk sizes)

A hit means a chunk from the expected document *and* page (PDF) or section (DOCX/TXT) is in the top 5. MRR rewards finding it early.

| Chunk size | Mode | Hit rate@5 | MRR | Misses |
|---|---|---|---|---|
| 500 | hybrid | 93 % | 0.773 | q06, q11 |
| 500 | dense | 87 % | 0.756 | q06, q07, q09, q16 |
| 500 | bm25 | 93 % | 0.797 | q06, q12 |
| 800 | hybrid | 90 % | 0.750 | q06, q07, q11 |
| 800 | dense | 83 % | 0.704 | q06, q07, q09, q11, q16 |
| 800 | bm25 | 93 % | 0.819 | q06, q12 |
| 1000 | hybrid | 90 % | 0.764 | q06, q07, q11 |
| 1000 | dense | 83 % | 0.721 | q06, q07, q09, q11, q16 |
| 1000 | bm25 | 93 % | 0.819 | q06, q12 |

## Answer quality (chunk size 800)

Correct = judge score 2 of 2 against the reference answer. Faithful = every claim in the answer is supported by the cited chunks. Refusal accuracy = share of unanswerable questions that were refused.

| Mode | Answered | Correct | Mean score | Faithful | Refusal acc. | Latency mean | Latency p95 | Est. cost |
|---|---|---|---|---|---|---|---|---|
| hybrid | 100 % | 83 % | 85 % | 90 % | 80 % | 4.0 s | 5.8 s | $0.0000 |
| dense | 100 % | 83 % | 85 % | 87 % | 80 % | 3.6 s | 5.2 s | $0.0000 |
| bm25 | 97 % | 87 % | 87 % | 97 % | 80 % | 3.5 s | 5.4 s | $0.0000 |

## Failures worth a look

- **q06 / hybrid** – Welche Reinheitsklasse ist für die Hydraulikflüssigkeit der RA-HP 450 vorgeschrieben?  
  answer: Die Reinheitsklasse für die Hydraulikflüssigkeit der RA-HP 450 wird in den gegebenen Kontextpassagen nicht erwähnt.  
  issue: correctness 0/2: Die Kandidatin antwortet falsch, obwohl die Referenzantwort existiert und die Reinheitsklasse genannt wird.; unsupported claim
- **q07 / hybrid** – Wie hoch ist der Wirkungsgrad des Netzteils RA-PS 24/40?  
  answer: Der Wirkungsgrad des Netzteils RA-PS 24/40 wird in den angegebenen Kontextpassagen nicht erwähnt.  
  issue: correctness 0/2: Die Kandidatin gibt an, dass der Wirkungsgrad nicht erwähnt wird, obwohl der Referenzantwort nachzulesen ist.; unsupported claim
- **q11 / hybrid** – At what internal temperature does the RA-PS 24/40 power supply switch off?  
  answer: The RA-PS 24/40 power supply has an operating temperature range of -25 °C to +70 °C, with derating starting at +55 °C. However, the context does not specify the exact internal temperature at which the  
  issue: correctness 1/2: The candidate correctly mentions the operating temperature range and derating but does not state the exact internal temperature at which the power supply switch; unsupported claim
- **q13 / hybrid** – Wie viel Skonto gibt es bei Zahlung innerhalb von 14 Tagen?  
  answer: 3 % Skonto [1].  
  issue: correctness 0/2: 
- **q24 / hybrid** – Wie hoch ist die Hotel-Obergrenze pro Nacht in München?  
  answer: Die Hotel-Obergrenze pro Nacht in München beträgt 180 Euro [1].  
  issue: correctness 0/2: 
- **u02 / hybrid** – Wie viele Mitarbeitende arbeiten am Standort Brno?  
  answer: Die Anzahl der Mitarbeitende am Standort Brno wird nicht explizit genannt. Es wird nur erwähnt, dass die Gesellschaft drei Standorte hat: Lörrach (Headquarter und Hydraulikwerk), Weil am Rhein (Leistu  
  issue: answered an unanswerable question
- **q06 / dense** – Welche Reinheitsklasse ist für die Hydraulikflüssigkeit der RA-HP 450 vorgeschrieben?  
  answer: Die Reinheitsklasse für die Hydraulikflüssigkeit der RA-HP 450 wird in den gegebenen Kontextpassagen nicht erwähnt.  
  issue: correctness 0/2: Die Kandidatin antwortet falsch, obwohl die Referenzantwort existiert und die Reinheitsklasse genannt wird.; unsupported claim
- **q07 / dense** – Wie hoch ist der Wirkungsgrad des Netzteils RA-PS 24/40?  
  answer: Der Wirkungsgrad des Netzteils RA-PS 24/40 wird in den angegebenen Kontextpassagen nicht erwähnt.  
  issue: correctness 0/2: Die Kandidatin gibt an, dass der Wirkungsgrad nicht erwähnt wird, obwohl der Referenzantwort nachzulesen ist.; unsupported claim
- **q11 / dense** – At what internal temperature does the RA-PS 24/40 power supply switch off?  
  answer: The RA-PS 24/40 power supply has an operating ambient temperature range of -25 °C to +70 °C, with derating starting at +55 °C. However, the context does not specify the internal temperature at which t  
  issue: correctness 1/2: The candidate correctly mentions the operating temperature range but does not provide the internal temperature at which the power supply switches off, which is ; unsupported claim
- **q16 / dense** – Welcher Gerichtsstand gilt für den Rahmenliefervertrag?  
  answer: Die Frage wird in den gegebenen Kontextpassagen nicht beantwortet.  
  issue: correctness 0/2: Die Kandidatin gibt an, dass die Frage nicht beantwortet wird, obwohl die Referenzantwort existiert und die Antwort bekannt ist.; unsupported claim
- **q24 / dense** – Wie hoch ist die Hotel-Obergrenze pro Nacht in München?  
  answer: Die Hotel-Obergrenze pro Nacht in München beträgt 180 Euro [1].  
  issue: correctness 0/2: 
- **u02 / dense** – Wie viele Mitarbeitende arbeiten am Standort Brno?  
  answer: Die Rheintal Antriebstechnik GmbH beschäftigt insgesamt etwa 850 Mitarbeitende an drei Standorten, wobei der Standort Brno in der Tschechischen Republik den Bereich Montage abdeckt [4]. Die genaue Anz  
  issue: answered an unanswerable question
- **q06 / bm25** – Welche Reinheitsklasse ist für die Hydraulikflüssigkeit der RA-HP 450 vorgeschrieben?  
  answer: Die Reinheitsklasse für die Hydraulikflüssigkeit der RA-HP 450 wird in den gegebenen Kontextpassagen nicht erwähnt.  
  issue: correctness 0/2: Die Kandidatin antwortet falsch, obwohl die Referenzantwort existiert und die Reinheitsklasse genannt wird.; unsupported claim
- **q11 / bm25** – At what internal temperature does the RA-PS 24/40 power supply switch off?  
  answer: I don't know. The uploaded documents do not contain information that answers this question.  
  issue: refused although answerable
- **q12 / bm25** – Wie lange läuft der Rahmenliefervertrag und wie ist die Kündigungsfrist?  
  answer: Die Dauer des Rahmenliefervertrags wird nicht explizit genannt [1]. Die Kündigungsfrist wird ebenfalls nicht angegeben [1].  
  issue: correctness 0/2: Der Kandidat gibt an, dass keine Informationen zur Dauer und Kündigungsfrist im Referenzdokument stehen, obwohl diese explizit genannt werden.
- **q13 / bm25** – Wie viel Skonto gibt es bei Zahlung innerhalb von 14 Tagen?  
  answer: 3 % Skonto [1].  
  issue: correctness 0/2: 
- **q24 / bm25** – Wie hoch ist die Hotel-Obergrenze pro Nacht in München?  
  answer: Die Hotel-Obergrenze pro Nacht in München beträgt 180 Euro [1].  
  issue: correctness 0/2: 
- **u02 / bm25** – Wie viele Mitarbeitende arbeiten am Standort Brno?  
  answer: Nach der Angabe in der Datei Onboarding_Guide_New_Employees.txt arbeiten etwa 850 Mitarbeitende in drei Standorten, wobei der Standort Brno in der Tschechischen Republik den Bereich der Montage überni  
  issue: answered an unanswerable question

## Notes

- Cost is estimated from an approximate token count (4 characters per token) and the price table in `app/llm.py`; local Ollama models cost $0.
- Latency includes retrieval, the LLM call and, for follow-ups, query rewriting. On a laptop with Ollama it is dominated by token generation.
- The judge is an LLM and can be wrong; spot-check the failures section.
