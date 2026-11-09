# GraphRAG Evaluation Framework

Comprehensive, multi-stage evaluation framework for the Test & Quality Management GraphRAG system.

---

## 🏗️ Architecture & Evaluation Pipeline

The evaluation framework measures performance across **4 distinct stages** per test case to isolate exact failure points without modifying existing pipeline code:

```
Question → [Stage 1: Entity/Intent Extraction] → [Stage 2: Routing] → [Stage 3: Retrieval] → [Stage 4: Final Answer & Judge]
```

### 📊 The 4 Evaluation Stages

1. **Stage 1: Entity/Intent Extraction** (No LLM Cost)
   * Entity Precision, Recall, and Exact Match for `test_case_ids`, `execution_ids`, `defect_ids`.
   * Intent Classification Exact Match.
2. **Stage 2: Retrieval Routing** (No LLM Cost)
   * Exact Match between chosen route (`neo4j` | `lightrag` | `hybrid`) and expected route.
   * Per-route confusion matrix generation.
3. **Stage 3: Retrieval Layer** (No LLM Cost)
   * **Neo4j Routes**: Gold field value recall (`hits / total_fields`), ID set Precision/Recall/F1 for list golds.
   * **LightRAG / Hybrid Routes**: Entity recall for broad aggregated gold targets.
   * Empty retrieval detection & unanswerable fallback checks.
4. **Stage 4: Final Answer & LLM Judge**
   * **Deterministic Scoring**: Exact numeric match for counts, normalized substring match for short metadata, token-level F1 (threshold $\ge 0.5$) for long descriptions/root causes, and unanswerable fallback verification.
   * **LLM Judge (Optional)**: Faithfulness (claims verification against retrieved context) and Completeness (question coverage) via `endpoint`, `export` (Kaggle), or `import`.

---

## 📁 Directory Structure (`graph/evaluation/`)

| File | Purpose |
| :--- | :--- |
| **`config.py`** | Environment variable configuration (`.env`), intent aliases, scoring thresholds, and regex patterns. |
| **`scorers.py`** | Small, pure scoring functions for entity extraction, intent match, routing match, retrieval recall, and answer correctness. |
| **`judge.py`** | LLM judge module supporting `none`, `endpoint`, `export` (Kaggle notebook script), and `import` backends. |
| **`report.py`** | Report generator creating `summary.md`, `summary.csv`, and detailed `failures.csv`. |
| **`run_eval.py`** | CLI entry point with progress bar (`tqdm`), immediate line-by-line checkpointing (`results.jsonl`), and `--resume` support. |
| **`test_scorers.py`** | Unit test suite verifying all scoring functions using `pytest`. |

---

## 🚀 How to Run

### 1. Run Unit Tests for Scoring Functions
Verify that all scoring logic functions correctly:
```bash
pytest graph/evaluation/test_scorers.py
```

### 2. Run Smoke Test (5 Cases, Zero API Cost for Judge)
Run a quick end-to-end smoke test on 5 cases:
```bash
python -m graph.evaluation.run_eval --limit 5 --judge none
```

### 3. Run Full Evaluation Benchmark
Run the full 210-case evaluation benchmark:
```bash
python -m graph.evaluation.run_eval --testset graph/testset.json --judge none
```

### 4. Resume an Interrupted Evaluation Run
If a run was stopped, use `--resume` to skip already evaluated test cases:
```bash
python -m graph.evaluation.run_eval --testset graph/testset.json --resume
```

### 5. Evaluate Specific Question Types
Target specific question types (e.g. `defect_lookup`, `testcase_to_defects`):
```bash
python -m graph.evaluation.run_eval --types defect_lookup,testcase_to_defects
```

---

## 🦙 Free Offline LLM Judge via Kaggle (Optional)

To run the LLM Judge (Faithfulness & Completeness) for free using a local/Kaggle GPU instance:

1. Run the evaluation with `--judge export`:
   ```bash
   python -m graph.evaluation.run_eval --testset graph/testset.json --judge export
   ```
   * This outputs `judge_inputs.jsonl` and `judge_kaggle_notebook.py` into the run directory.

2. Upload `judge_inputs.jsonl` and `judge_kaggle_notebook.py` to a free Kaggle GPU notebook (T4 / P100) and execute it.
   * It uses `vLLM` and `Qwen/Qwen2.5-7B-Instruct-AWQ` to score all items for free, saving `judge_outputs.jsonl`.

3. Download `judge_outputs.jsonl` back into the run directory and run `--judge import`:
   ```bash
   python -m graph.evaluation.run_eval --out graph/evaluation/runs/<timestamp> --judge import
   ```

---

## 📑 Output Artifacts

After every run, the following files are automatically created in `graph/evaluation/runs/<timestamp>/`:
* **`summary.md`**: Markdown report with overall metrics, failure funnel, per-type breakdown, hop count accuracy, and routing confusion matrix.
* **`summary.csv`**: CSV export of metric tables.
* **`failures.csv`**: Detailed log of every failing test case containing the question, gold answer, retrieved snippet, answer text, and `first_failing_stage`.
* **`results.jsonl`**: Checkpointed line-by-line record of raw results for all evaluated test cases.
* **`run_meta.json`**: Metadata containing timestamp, testset file hash, and execution settings.
