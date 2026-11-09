import json
import re
import unicodedata
from typing import Dict, Any, List, Set, Tuple, Optional

# Dash and Quote translation tables
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")
_QUOTES = dict.fromkeys(map(ord, "\u201c\u201d\u2018\u2019"), None)


def normalize_text(text: str) -> str:
    """
    Normalize text: NFKC unicode normalization, translate dashes/quotes,
    convert to lowercase, collapse whitespace, and strip.
    """
    if not text:
        return ""
    s = str(text)
    s = unicodedata.normalize("NFKC", s).translate(_DASHES).translate(_QUOTES).lower()
    return re.sub(r"\s+", " ", s).strip()


def normalize_id(entity_id: str) -> str:
    """Normalize entity ID: translate dashes, uppercase, and strip whitespace."""
    if not entity_id:
        return ""
    s = str(entity_id).translate(_DASHES).strip().upper()
    return s


def score_extraction(
    extracted_entities: Optional[Dict[str, List[str]]],
    expected_entities: Optional[Dict[str, List[str]]]
) -> Dict[str, Any]:
    """Score entity extraction accuracy for test_case_ids, execution_ids, and defect_ids."""
    extracted_entities = extracted_entities or {}
    expected_entities = expected_entities or {}

    keys = ["test_case_ids", "execution_ids", "defect_ids"]
    scores = {}
    all_exact_match = True

    for key in keys:
        extracted_set = {normalize_id(x) for x in extracted_entities.get(key, []) if x}
        expected_set = {normalize_id(x) for x in expected_entities.get(key, []) if x}

        if not expected_set:
            precision = 1.0 if not extracted_set else 0.0
            recall = 1.0
            exact_match = (len(extracted_set) == 0)
        else:
            tp = len(extracted_set & expected_set)
            fp = len(extracted_set - expected_set)
            fn = len(expected_set - extracted_set)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            exact_match = (extracted_set == expected_set)

        if not exact_match:
            all_exact_match = False

        scores[key] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "exact_match": exact_match
        }

    scores["overall_exact_match"] = all_exact_match
    return scores


def score_intent(
    extracted_intent: str,
    expected_intent: str,
    aliases: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    Score query intent classification.
    Reports both raw exact match and aliased match so naming mismatches are visible.
    """
    extracted_raw = str(extracted_intent or "").strip().lower()
    expected_raw = str(expected_intent or "").strip().lower()

    raw_match = (extracted_raw == expected_raw)

    aliased_match = raw_match
    if not aliased_match and aliases and expected_raw in aliases:
        aliased_match = extracted_raw in [a.lower() for a in aliases[expected_raw]]

    return {
        "extracted_intent": extracted_intent,
        "expected_intent": expected_intent,
        "intent_acc_raw": raw_match,
        "intent_acc_aliased": aliased_match,
        "intent_exact_match": aliased_match  # for backward compatibility
    }


def score_routing(chosen_route: str, expected_route: str) -> Dict[str, Any]:
    """Score retrieval routing decision exact match."""
    chosen = normalize_text(chosen_route)
    expected = normalize_text(expected_route)

    return {
        "chosen_route": chosen,
        "expected_route": expected,
        "route_exact_match": (chosen == expected)
    }


def extract_ids_from_text(text: str) -> Dict[str, List[str]]:
    """
    Extract entity IDs (BUG-*, TC-*, EXEC-*, SCR-*) from raw text using case-insensitive regex
    and normalizing non-standard hyphens.
    """
    if not text:
        return {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []}

    text_str = str(text).translate(_DASHES)

    defects = sorted(list({normalize_id(m) for m in re.findall(r"\bBUG-\d+\b", text_str, re.IGNORECASE)}))
    tcs = sorted(list({normalize_id(m) for m in re.findall(r"\bTC-\d+\b", text_str, re.IGNORECASE)}))
    execs = sorted(list({normalize_id(m) for m in re.findall(r"\bEXEC-\d+\b", text_str, re.IGNORECASE)}))
    scs = sorted(list({normalize_id(m) for m in re.findall(r"\bSCR-[A-Za-z0-9_\-]+\b", text_str, re.IGNORECASE)}))

    return {
        "defect_ids": defects,
        "test_case_ids": tcs,
        "execution_ids": execs,
        "screenshot_ids": scs
    }


def compute_text_metrics(pred_text: str, gold_text: str) -> Dict[str, Any]:
    """
    Compute text matching metrics:
      1. Substring match (punctuation-stripped)
      2. Gold token recall (share of gold tokens in pred_text)
      3. Token F1 and Precision
    """
    norm_pred = normalize_text(pred_text)
    norm_gold = normalize_text(gold_text)

    # Strip punctuation for substring check
    clean_pred = re.sub(r"[^\w\s]", "", norm_pred)
    clean_gold = re.sub(r"[^\w\s]", "", norm_gold)

    substring_match = (clean_gold != "" and clean_gold in clean_pred)

    gold_tokens = re.findall(r"\w+", norm_gold)
    pred_tokens = re.findall(r"\w+", norm_pred)

    if not gold_tokens:
        return {
            "substring_match": True,
            "gold_recall": 1.0,
            "token_precision": 1.0,
            "token_f1": 1.0,
            "pass_text": True
        }

    if not pred_tokens:
        return {
            "substring_match": False,
            "gold_recall": 0.0,
            "token_precision": 0.0,
            "token_f1": 0.0,
            "pass_text": False
        }

    pred_counts = {}
    for t in pred_tokens:
        pred_counts[t] = pred_counts.get(t, 0) + 1

    gold_counts = {}
    for t in gold_tokens:
        gold_counts[t] = gold_counts.get(t, 0) + 1

    overlap = 0
    for t, count in gold_counts.items():
        if t in pred_counts:
            overlap += min(count, pred_counts[t])

    gold_recall = overlap / len(gold_tokens)
    token_precision = overlap / len(pred_tokens)
    token_f1 = (2 * token_precision * gold_recall / (token_precision + gold_recall)) if (token_precision + gold_recall) > 0 else 0.0

    pass_text = substring_match or (gold_recall >= 0.8)

    return {
        "substring_match": substring_match,
        "gold_recall": round(gold_recall, 4),
        "token_precision": round(token_precision, 4),
        "token_f1": round(token_f1, 4),
        "pass_text": pass_text
    }


def detect_reasoning_leak(answer_text: str, regexes: Optional[List[re.Pattern]] = None) -> bool:
    """Detect if an answer contains chain-of-thought or internal reasoning leakage."""
    if not answer_text:
        return False
    if regexes is None:
        from graph.evaluation.config import REASONING_LEAK_REGEXES
        regexes = REASONING_LEAK_REGEXES
    return any(p.search(answer_text) for p in regexes)


def score_retrieval(
    retrieved_context: Any,
    gold_answer: Optional[Dict[str, Any]],
    route: str,
    min_field_recall: Optional[float] = None
) -> Dict[str, Any]:
    """Score Stage 3: Retrieval performance with configurable strict recall threshold."""
    if min_field_recall is None:
        from graph.evaluation.config import RETRIEVAL_MIN_FIELD_RECALL
        min_field_recall = RETRIEVAL_MIN_FIELD_RECALL

    context_str = json.dumps(retrieved_context, ensure_ascii=False) if isinstance(retrieved_context, (dict, list)) else str(retrieved_context or "")
    flat_context = normalize_text(context_str)

    is_empty = (len(flat_context.strip()) == 0 or flat_context.strip() in ["[]", "{}", "null", "none"])

    # Unanswerable cases (gold_answer is None)
    if gold_answer is None:
        pass_unanswerable = is_empty or "no record" in flat_context or "not found" in flat_context
        return {
            "empty_retrieval": is_empty,
            "field_recall": 1.0 if pass_unanswerable else 0.0,
            "set_precision": None,
            "set_recall": None,
            "set_f1": None,
            "entity_recall": None,
            "missing_fields": [],
            "pass_retrieval": pass_unanswerable,
            "details": "Unanswerable query context check"
        }

    # Answerable cases with empty retrieval -> Retrieval failure
    if is_empty:
        missing_keys = [k for k, v in gold_answer.items() if v is not None and v != "" and v != []]
        return {
            "empty_retrieval": True,
            "field_recall": 0.0,
            "set_precision": None,
            "set_recall": None,
            "set_f1": None,
            "entity_recall": 0.0,
            "missing_fields": missing_keys,
            "pass_retrieval": False,
            "details": "Empty context returned for answerable query"
        }

    total_fields = 0
    hits = 0
    missing_fields = []

    set_precision = None
    set_recall = None
    set_f1 = None
    entity_recall = None

    # For broad summary or list golds
    if route.lower() in ["lightrag", "hybrid"] and isinstance(gold_answer, dict):
        gold_items = []
        for v in gold_answer.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        gold_items.extend([str(val).strip() for val in item.values() if str(val).strip()])
                    elif item:
                        gold_items.append(str(item).strip())
            elif v:
                gold_items.append(str(v).strip())

        if gold_items:
            found_items = 0
            for item in gold_items:
                if normalize_text(item) in flat_context:
                    found_items += 1
                else:
                    missing_fields.append(item)
            entity_recall = round(found_items / len(gold_items), 4)
            field_recall = entity_recall
        else:
            field_recall = 1.0

        pass_ret = (field_recall >= min_field_recall)
        return {
            "empty_retrieval": False,
            "field_recall": field_recall,
            "set_precision": None,
            "set_recall": None,
            "set_f1": None,
            "entity_recall": entity_recall,
            "missing_fields": missing_fields,
            "pass_retrieval": pass_ret
        }

    # Neo4j routes: check scalar fields & list fields
    extracted_ids = extract_ids_from_text(context_str)

    for field, val in gold_answer.items():
        if val is None or val == "" or val == []:
            continue

        total_fields += 1

        if field == "defect_ids" and isinstance(val, list):
            gold_set = {normalize_id(x) for x in val}
            found_set = set(extracted_ids["defect_ids"])

            tp = len(gold_set & found_set)
            fp = len(found_set - gold_set)
            fn = len(gold_set - found_set)

            set_precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
            set_recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
            set_f1 = round(2 * (set_precision * set_recall) / (set_precision + set_recall), 4) if (set_precision + set_recall) > 0 else 0.0

            if set_recall > 0:
                hits += 1
            else:
                missing_fields.append(field)

        elif isinstance(val, list):
            val_strs = [normalize_text(str(x)) for x in val if str(x).strip()]
            if any(v in flat_context for v in val_strs):
                hits += 1
            else:
                missing_fields.append(field)
        else:
            val_str = normalize_text(str(val))
            if val_str in flat_context:
                hits += 1
            else:
                missing_fields.append(field)

    field_recall = round(hits / total_fields, 4) if total_fields > 0 else 1.0
    pass_ret = (field_recall >= min_field_recall)

    return {
        "empty_retrieval": False,
        "field_recall": field_recall,
        "set_precision": set_precision,
        "set_recall": set_recall,
        "set_f1": set_f1,
        "entity_recall": entity_recall,
        "missing_fields": missing_fields,
        "pass_retrieval": pass_ret
    }



def score_final_answer(
    answer_text: str,
    gold_answer: Optional[Dict[str, Any]],
    qtype: str = "",
    scored_fields_map: Optional[Dict[str, List[str]]] = None,
    unanswerable_regexes: Optional[List[re.Pattern]] = None,
    refusal_regexes: Optional[List[re.Pattern]] = None
) -> Dict[str, Any]:
    """
    Score Stage 4: Deterministic Final Answer evaluation.
    Only scores the fields requested by the question intent/type.
    """
    norm_ans = normalize_text(answer_text)

    # Check for Refusal / Safety Classifier Label outputs
    if refusal_regexes and any(pattern.search(answer_text) for pattern in refusal_regexes):
        return {
            "answer_correctness": 0.0,
            "pass_answer": False,
            "refusal_detected": True,
            "failed_fields": ["refusal_safety_label_detected"],
            "details": "Answer step returned a refusal or safety-classifier label"
        }

    # Unanswerable evaluation
    if gold_answer is None:
        has_fallback_phrase = False
        if unanswerable_regexes:
            has_fallback_phrase = any(pattern.search(answer_text) for pattern in unanswerable_regexes)
        else:
            has_fallback_phrase = any(p in norm_ans for p in ["not found", "no record", "does not exist", "unable to find", "no defect"])

        extracted_ids = extract_ids_from_text(answer_text)
        has_invented_ids = (len(extracted_ids["defect_ids"]) > 0 or len(extracted_ids["test_case_ids"]) > 0 or len(extracted_ids["execution_ids"]) > 0)

        pass_unanswerable = has_fallback_phrase and not has_invented_ids
        return {
            "answer_correctness": 1.0 if pass_unanswerable else 0.0,
            "pass_answer": pass_unanswerable,
            "failed_fields": [] if pass_unanswerable else ["unanswerable_fallback_phrase_missing_or_invented_ids"],
            "details": f"Fallback phrase: {has_fallback_phrase}, Invented IDs: {has_invented_ids}"
        }

    # Determine which fields to score based on qtype
    allowed_fields = None
    if scored_fields_map and qtype in scored_fields_map:
        allowed_fields = scored_fields_map[qtype]

    total_fields = 0
    matched_fields = 0
    field_details = {}
    failed_fields = []

    for field, val in gold_answer.items():
        if val is None or val == "" or val == []:
            continue

        # Filter unrequested metadata fields
        if allowed_fields is not None and field not in allowed_fields:
            continue

        total_fields += 1
        matched = False
        reason = ""

        # Numbers
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            numbers_in_ans = [int(n) for n in re.findall(r"\b\d+\b", answer_text)]
            matched = (int(val) in numbers_in_ans)
            reason = f"Expected number {val} in answer numbers {numbers_in_ans}"

        # Long text (root_cause, title, description)
        elif field in ["root_cause", "title", "description"]:
            t_metrics = compute_text_metrics(answer_text, str(val))
            matched = t_metrics["pass_text"]
            reason = f"Recall: {t_metrics['gold_recall']}, Substring: {t_metrics['substring_match']}"
            field_details[f"{field}_metrics"] = t_metrics

        # List fields (e.g. defect_ids, or list of dicts for aggregations/broad_summary)
        elif isinstance(val, list):
            if all(isinstance(x, dict) for x in val):
                matched_dicts = 0
                for d in val:
                    d_matched = True
                    for k_inner, v_inner in d.items():
                        if v_inner is None:
                            continue
                        if isinstance(v_inner, (int, float)) and not isinstance(v_inner, bool):
                            numbers_in_ans = [int(n) for n in re.findall(r"\b\d+\b", answer_text)]
                            if int(v_inner) not in numbers_in_ans:
                                d_matched = False
                                break
                        elif k_inner in ["root_cause", "title", "description"]:
                            t_metrics = compute_text_metrics(answer_text, str(v_inner))
                            if not t_metrics["pass_text"]:
                                d_matched = False
                                break
                        else:
                            if normalize_text(str(v_inner)) not in norm_ans:
                                d_matched = False
                                break
                    if d_matched:
                        matched_dicts += 1
                matched = (matched_dicts == len(val)) if val else True
                reason = f"Matched {matched_dicts}/{len(val)} dict items"
            else:
                gold_items = [normalize_text(str(x)) for x in val if str(x).strip()]
                found_items = [item for item in gold_items if item in norm_ans]
                matched = (len(found_items) == len(gold_items)) if gold_items else True
                reason = f"Matched {len(found_items)}/{len(gold_items)} items"

        # Short metadata values (IDs, status, severity, priority, build, tester, env, browser, OS)
        else:
            val_str = normalize_text(str(val))
            matched = (val_str in norm_ans)
            reason = f"Expected '{val_str}' substring match in answer"

        if matched:
            matched_fields += 1
        else:
            failed_fields.append(f"{field}: {reason}")

        field_details[field] = matched

    correctness = matched_fields / total_fields if total_fields > 0 else 1.0
    pass_answer = (matched_fields == total_fields) if total_fields > 0 else True

    return {
        "answer_correctness": round(correctness, 4),
        "matched_fields": matched_fields,
        "total_fields": total_fields,
        "pass_answer": pass_answer,
        "failed_fields": failed_fields,
        "field_details": field_details
    }
