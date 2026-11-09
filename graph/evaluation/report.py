import os
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from graph.evaluation.scorers import normalize_text


def dataframe_to_markdown(df: pd.DataFrame, index: bool = False) -> str:
    """Convert pandas DataFrame to markdown string with fallback if tabulate is missing."""
    try:
        return df.to_markdown(index=index)
    except Exception:
        cols = list(df.columns)
        header = "| " + " | ".join(str(c) for c in cols) + " |"
        sep = "| " + " | ".join("---" for _ in cols) + " |"
        lines = [header, sep]
        for _, row in df.iterrows():
            line = "| " + " | ".join(str(row[c]) for c in cols) + " |"
            lines.append(line)
        return "\n".join(lines)


def center_snippet_on_evidence(text: str, gold_answer: Any, max_chars: int = 1500) -> str:
    """Extract up to max_chars snippet centered around the evidence / gold values."""
    if not text:
        return ""
    text_str = str(text)

    if len(text_str) <= max_chars:
        return text_str

    # Search for first gold value hit in text
    target_pos = -1
    if isinstance(gold_answer, dict):
        for val in gold_answer.values():
            if val and not isinstance(val, (dict, list)):
                val_str = str(val).strip()
                if val_str and len(val_str) > 3:
                    pos = text_str.lower().find(val_str.lower())
                    if pos != -1:
                        target_pos = pos
                        break

    if target_pos == -1:
        # Look for "structured_evidence" or "results"
        pos = text_str.lower().find("structured_evidence")
        if pos != -1:
            target_pos = pos

    if target_pos == -1:
        target_pos = 0

    half = max_chars // 2
    start = max(0, target_pos - half)
    end = min(len(text_str), start + max_chars)

    snippet = text_str[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text_str):
        snippet = snippet + "..."

    return snippet


def generate_reports(results: List[Dict[str, Any]], run_meta: Dict[str, Any], out_dir: str):
    """
    Generate comprehensive evaluation reports:
      1. summary.md  (Rich markdown summary with raw & aliased intent accuracy)
      2. summary.csv & detailed metric CSVs
      3. failures.csv (Detailed failures breakdown with 1500-char evidence snippets and failed fields)
    """
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(results)

    if df.empty:
        print("[WARNING] Results dataset is empty. Cannot generate report.")
        return

    # Exclude infrastructure errors from accuracy denominators
    valid_df = df[df["first_failing_stage"] != "infra_error"].copy()
    infra_count = len(df) - len(valid_df)

    if valid_df.empty:
        valid_df = df.copy()

    # Extract score columns safely
    valid_df["ext_exact"] = valid_df["scores"].apply(lambda s: s.get("extraction", {}).get("overall_exact_match", False))
    valid_df["intent_raw"] = valid_df["scores"].apply(lambda s: s.get("intent", {}).get("intent_acc_raw", False))
    valid_df["intent_aliased"] = valid_df["scores"].apply(lambda s: s.get("intent", {}).get("intent_acc_aliased", False))
    valid_df["route_exact"] = valid_df["scores"].apply(lambda s: s.get("routing", {}).get("route_exact_match", False))

    valid_df["ret_field_recall"] = valid_df["scores"].apply(lambda s: s.get("retrieval", {}).get("field_recall", 0.0))
    valid_df["ret_empty"] = valid_df["scores"].apply(lambda s: s.get("retrieval", {}).get("empty_retrieval", False))

    valid_df["ans_correctness"] = valid_df["scores"].apply(lambda s: s.get("final_answer", {}).get("answer_correctness", 0.0))
    valid_df["judge_faithfulness"] = valid_df["scores"].apply(lambda s: s.get("judge", {}).get("faithfulness", np.nan))
    valid_df["judge_completeness"] = valid_df["scores"].apply(lambda s: s.get("judge", {}).get("completeness", np.nan))

    # Unanswerable pass rate
    unanswerable_df = valid_df[valid_df["type"] == "unanswerable"]
    unans_pass_rate = (unanswerable_df["first_failing_stage"] == "none").mean() if not unanswerable_df.empty else np.nan

    # Latencies
    latencies = valid_df["total_latency_sec"].values if "total_latency_sec" in valid_df.columns else np.array([0.0])
    p50_lat = np.percentile(latencies, 50) if len(latencies) > 0 else 0.0
    p95_lat = np.percentile(latencies, 95) if len(latencies) > 0 else 0.0

    # -------------------------------------------------------------------------
    # 1. Overall Summary Table
    # -------------------------------------------------------------------------
    overall_metrics = {
        "Total Test Cases": len(df),
        "Valid Pipeline Cases Evaluated": len(valid_df),
        "Infrastructure Failures Excluded": infra_count,
        "Extraction Exact Match": f"{valid_df['ext_exact'].mean() * 100:.1f}%",
        "Intent Accuracy (Raw Strict)": f"{valid_df['intent_raw'].mean() * 100:.1f}%",
        "Intent Accuracy (Aliased)": f"{valid_df['intent_aliased'].mean() * 100:.1f}%",
        "Routing Accuracy": f"{valid_df['route_exact'].mean() * 100:.1f}%",
        "Retrieval Field Recall": f"{valid_df['ret_field_recall'].mean() * 100:.1f}%",
        "Empty Retrieval Rate": f"{valid_df['ret_empty'].mean() * 100:.1f}%",
        "Answer Correctness": f"{valid_df['ans_correctness'].mean() * 100:.1f}%",
        "Unanswerable Pass Rate": f"{unans_pass_rate * 100:.1f}%" if not np.isnan(unans_pass_rate) else "N/A",
        "Faithfulness (Judge)": f"{valid_df['judge_faithfulness'].dropna().mean() * 100:.1f}%" if valid_df["judge_faithfulness"].dropna().count() > 0 else "N/A",
        "Completeness (Judge)": f"{valid_df['judge_completeness'].dropna().mean() * 100:.1f}%" if valid_df["judge_completeness"].dropna().count() > 0 else "N/A",
        "Latency p50": f"{p50_lat:.2f}s",
        "Latency p95": f"{p95_lat:.2f}s"
    }

    # -------------------------------------------------------------------------
    # 2. Per Question Type Breakdown
    # -------------------------------------------------------------------------
    type_rows = []
    for qtype, gdf in valid_df.groupby("type"):
        type_rows.append({
            "Question Type": qtype,
            "Count": len(gdf),
            "Extraction Match %": f"{gdf['ext_exact'].mean() * 100:.1f}%",
            "Intent Raw %": f"{gdf['intent_raw'].mean() * 100:.1f}%",
            "Intent Aliased %": f"{gdf['intent_aliased'].mean() * 100:.1f}%",
            "Routing Acc %": f"{gdf['route_exact'].mean() * 100:.1f}%",
            "Retrieval Field Recall %": f"{gdf['ret_field_recall'].mean() * 100:.1f}%",
            "Answer Correctness %": f"{gdf['ans_correctness'].mean() * 100:.1f}%",
            "Pass Rate %": f"{(gdf['first_failing_stage'] == 'none').mean() * 100:.1f}%"
        })
    type_df = pd.DataFrame(type_rows)

    # -------------------------------------------------------------------------
    # 3. Per Route & Confusion Matrix (Excludes error routes)
    # -------------------------------------------------------------------------
    route_rows = []
    for rtype, gdf in valid_df.groupby("expected_route"):
        route_rows.append({
            "Expected Route": rtype,
            "Count": len(gdf),
            "Routing Acc %": f"{gdf['route_exact'].mean() * 100:.1f}%",
            "Retrieval Field Recall %": f"{gdf['ret_field_recall'].mean() * 100:.1f}%",
            "Answer Correctness %": f"{gdf['ans_correctness'].mean() * 100:.1f}%"
        })
    route_df = pd.DataFrame(route_rows)

    # Clean confusion matrix without "error" or "infra_error" columns
    clean_route_df = valid_df[valid_df["chosen_route"].isin(["neo4j", "lightrag", "hybrid"])]
    if not clean_route_df.empty:
        conf_df = pd.crosstab(clean_route_df["expected_route"], clean_route_df["chosen_route"], rownames=["Expected"], colnames=["Chosen"])
    else:
        conf_df = pd.DataFrame(0, index=["neo4j", "lightrag", "hybrid"], columns=["neo4j", "lightrag", "hybrid"])

    # -------------------------------------------------------------------------
    # 4. Hop Count Breakdown
    # -------------------------------------------------------------------------
    hop_rows = []
    for hops, gdf in valid_df.groupby("hops"):
        hop_rows.append({
            "Hops": hops,
            "Count": len(gdf),
            "Routing Acc %": f"{gdf['route_exact'].mean() * 100:.1f}%",
            "Retrieval Field Recall %": f"{gdf['ret_field_recall'].mean() * 100:.1f}%",
            "Answer Correctness %": f"{gdf['ans_correctness'].mean() * 100:.1f}%",
            "Pass Rate %": f"{(gdf['first_failing_stage'] == 'none').mean() * 100:.1f}%"
        })
    hop_df = pd.DataFrame(hop_rows)

    # -------------------------------------------------------------------------
    # 5. Failure Funnel
    # -------------------------------------------------------------------------
    funnel_counts = df["first_failing_stage"].value_counts().to_dict()
    funnel_rows = [
        {"Stage": "extraction", "Failed First Count": int(funnel_counts.get("extraction", 0))},
        {"Stage": "routing", "Failed First Count": int(funnel_counts.get("routing", 0))},
        {"Stage": "retrieval", "Failed First Count": int(funnel_counts.get("retrieval", 0))},
        {"Stage": "generation", "Failed First Count": int(funnel_counts.get("generation", 0))},
        {"Stage": "infra_error", "Failed First Count": int(funnel_counts.get("infra_error", 0))},
        {"Stage": "none (All Passed)", "Failed First Count": int(funnel_counts.get("none", 0))}
    ]
    funnel_df = pd.DataFrame(funnel_rows)

    # -------------------------------------------------------------------------
    # Generate summary.md
    # -------------------------------------------------------------------------
    md_content = []
    md_content.append("# GraphRAG Evaluation Benchmark Report")
    md_content.append(f"**Run Timestamp**: `{run_meta.get('timestamp', '')}`\n")
    md_content.append(f"**Testset File**: `{run_meta.get('testset_path', '')}`\n")

    md_content.append("## 1. Overall System Performance")
    md_content.append("| Metric | Value |")
    md_content.append("| :--- | :--- |")
    for k, v in overall_metrics.items():
        md_content.append(f"| **{k}** | {v} |")

    md_content.append("\n## 2. Failure Funnel")
    md_content.append(dataframe_to_markdown(funnel_df, index=False))

    md_content.append("\n## 3. Performance by Question Type")
    md_content.append(dataframe_to_markdown(type_df, index=False))

    md_content.append("\n## 4. Performance by Hop Count")
    md_content.append(dataframe_to_markdown(hop_df, index=False))

    md_content.append("\n## 5. Routing Accuracy & Confusion Matrix")
    md_content.append(dataframe_to_markdown(route_df, index=False))
    md_content.append("\n### Routing Confusion Matrix")
    md_content.append(dataframe_to_markdown(conf_df, index=True))

    md_path = os.path.join(out_dir, "summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))

    # -------------------------------------------------------------------------
    # Save CSV outputs (summary.csv and detailed per-category CSVs)
    # -------------------------------------------------------------------------
    pd.DataFrame(list(overall_metrics.items()), columns=["Metric", "Value"]).to_csv(os.path.join(out_dir, "summary_overall.csv"), index=False)
    type_df.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    type_df.to_csv(os.path.join(out_dir, "summary_by_type.csv"), index=False)
    route_df.to_csv(os.path.join(out_dir, "summary_by_route.csv"), index=False)
    hop_df.to_csv(os.path.join(out_dir, "summary_by_hops.csv"), index=False)
    funnel_df.to_csv(os.path.join(out_dir, "summary_funnel.csv"), index=False)

    # -------------------------------------------------------------------------
    # Generate failures.csv with 1500-char evidence snippets & failed fields
    # -------------------------------------------------------------------------
    failures_df = df[df["first_failing_stage"] != "none"].copy()
    fail_rows = []
    for _, row in failures_df.iterrows():
        ctx = row.get("retrieved_context")
        gold = row.get("gold_answer")

        # Center evidence snippet around gold value hits
        ctx_snippet = center_snippet_on_evidence(ctx, gold, max_chars=1500)

        # Get failed fields details
        failed_fields_raw = row.get("failed_fields")
        if not failed_fields_raw:
            ans_scores = row.get("scores", {}).get("final_answer", {})
            failed_fields_raw = ans_scores.get("failed_fields", [])

        if isinstance(failed_fields_raw, list):
            failed_fields_str = "; ".join(str(f) for f in failed_fields_raw) if failed_fields_raw else "N/A"
        else:
            failed_fields_str = str(failed_fields_raw or "N/A")

        ans_snippet = str(row.get("answer") or row.get("generated_answer") or "")[:1500]

        fail_rows.append({
            "id": row.get("id"),
            "type": row.get("type"),
            "hops": row.get("hops"),
            "question": row.get("question"),
            "expected_route": row.get("expected_route"),
            "chosen_route": row.get("chosen_route"),
            "first_failing_stage": row.get("first_failing_stage"),
            "failed_fields": failed_fields_str,
            "gold_answer": json.dumps(gold, ensure_ascii=False),
            "retrieved_snippet": ctx_snippet,
            "answer": ans_snippet,
            "error_text": row.get("error_text", "")
        })

    fail_csv_path = os.path.join(out_dir, "failures.csv")
    pd.DataFrame(fail_rows).to_csv(fail_csv_path, index=False)

    print(f"\n[SUCCESS] Reports generated in {out_dir}:")
    print(f"  - summary.md")
    print(f"  - summary.csv")
    print(f"  - failures.csv ({len(failures_df)} failed cases logged)")
