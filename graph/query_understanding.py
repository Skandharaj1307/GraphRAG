import os
import json
import re
import unicodedata
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from graph.llm_client import (
    get_async_client,
    get_model_for_role,
    complete_chat,
    tolerant_json_parse,
    is_transient_error,
    LLMInfraError,
)


# ============================================================
# ERROR CLASSIFICATION
# ============================================================

def is_transient_error(error: Exception) -> bool:
    """Check if an exception represents an HTTP 429 rate limit or 5xx server error."""
    err_text = str(error).lower()
    return (
        "429" in err_text
        or "rate limit" in err_text
        or "rate_limited" in err_text
        or "500" in err_text
        or "502" in err_text
        or "503" in err_text
        or "504" in err_text
        or "bad gateway" in err_text
        or "service unavailable" in err_text
        or "gateway timeout" in err_text
    )


# ============================================================
# DETERMINISTIC NORMALIZATION & ID EXTRACTION
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize text with NFKC and map Unicode dashes to ASCII hyphen."""
    text = unicodedata.normalize("NFKC", text)
    dash_chars = ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"]
    for ch in dash_chars:
        text = text.replace(ch, "-")
    return text


def extract_regex_ids(text: str) -> Dict[str, List[str]]:
    """Extract deterministic IDs regardless of digit count, keeping exact casing."""
    norm_text = normalize_text(text)

    def _find(pattern: str, prefix: str) -> List[str]:
        found = []
        for m in re.finditer(pattern, norm_text, re.IGNORECASE):
            val = m.group(0)
            dash_idx = val.find("-")
            if dash_idx != -1:
                val = prefix.upper() + val[dash_idx:]
            if val not in found:
                found.append(val)
        return found

    return {
        "defect_ids": _find(r"\bBUG-\d+\b", "BUG"),
        "test_case_ids": _find(r"\bTC-\d+\b", "TC"),
        "execution_ids": _find(r"\bEXEC-\d+\b", "EXEC"),
        "screenshot_ids": _find(r"\bSCR-[A-Za-z0-9_]+-\d+\b", "SCR"),
    }


# ============================================================
# VOCABULARY VALIDATOR
# ============================================================

ALIASES = {
    "crit": "Critical",
    "critical": "Critical",
    "blocker": "Blocker",
    "major": "Major",
    "minor": "Minor",
    "p0": "P0",
    "p1": "P1",
    "p2": "P2",
    "p3": "P3",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "inprogress": "In Progress",
    "reopened": "Reopened",
    "resolved": "Resolved",
    "closed": "Closed",
    "new": "New",
    "passed": "Passed",
    "failed": "Failed",
    "skipped": "Skipped",
    "blocked": "Blocked",
    "dev": "DEV",
    "uat": "UAT",
    "qa": "QA",
    "staging": "STAGING",
    "yes": "Yes",
    "true": "Yes",
    "regression": "Yes",
    "no": "No",
    "false": "No",
}


def validate_and_map_filters(
    raw_filters: Dict[str, Any],
    vocabulary: Optional[Dict[str, List[str]]] = None,
) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Validate filter values case-insensitively against vocabulary."""
    if not vocabulary:
        return dict(raw_filters), []

    validated = {}
    unmapped = []

    vocab_lookup = {
        "severity": {v.lower(): v for v in vocabulary.get("severity", [])},
        "priority": {v.lower(): v for v in vocabulary.get("priority", [])},
        "status": {
            **{v.lower(): v for v in vocabulary.get("status", [])},
            **{v.lower(): v for v in vocabulary.get("execution_status", [])},
        },
        "bug_type": {v.lower(): v for v in vocabulary.get("bug_type", [])},
        "environment": {v.lower(): v for v in vocabulary.get("environments", [])},
        "module": {v.lower(): v for v in vocabulary.get("modules", [])},
        "regression": {"yes": "Yes", "no": "No", "true": "Yes", "false": "No"},
    }

    for k, raw_v in raw_filters.items():
        if raw_v is None:
            continue

        # Map key aliases
        if k in ("type", "defect_type"):
            if str(raw_v).lower() in ("regression", "yes", "regression bugs", "regression bug"):
                k = "regression"
                raw_v = "Yes"
            else:
                k = "bug_type"

        target_vocab = vocab_lookup.get(k)

        items_to_check = []
        if isinstance(raw_v, (list, tuple, set)):
            items_to_check = [str(x).strip() for x in raw_v if x is not None and str(x).strip()]
        else:
            v_str = str(raw_v).strip()
            if target_vocab is not None and ("," in v_str or " or " in v_str):
                parts = [p.strip() for p in re.split(r",|\bor\b", v_str) if p.strip()]
                if len(parts) > 1 and any(
                    p.lower() in target_vocab or ALIASES.get(p.lower(), p).lower() in target_vocab
                    for p in parts
                ):
                    items_to_check = parts
                else:
                    items_to_check = [v_str]
            else:
                items_to_check = [v_str]

        if target_vocab is not None:
            valid_items = []
            unmapped_items = []
            for item in items_to_check:
                item_lower = item.lower()
                aliased_v = ALIASES.get(item_lower, item)
                aliased_lower = aliased_v.lower()

                if aliased_lower in target_vocab:
                    valid_items.append(target_vocab[aliased_lower])
                elif item_lower in target_vocab:
                    valid_items.append(target_vocab[item_lower])
                else:
                    unmapped_items.append(item)

            if valid_items:
                if len(valid_items) == 1 and not isinstance(raw_v, (list, tuple, set)) and len(items_to_check) == 1:
                    validated[k] = valid_items[0]
                else:
                    validated[k] = list(dict.fromkeys(valid_items))

            if unmapped_items:
                unmapped.append({
                    "key": k,
                    "value": ", ".join(unmapped_items),
                    "reason": f"Value '{', '.join(unmapped_items)}' does not exist in {k} vocabulary",
                })
        else:
            # Low-cardinality or direct property (e.g. build_number, tester)
            if isinstance(raw_v, (list, tuple, set)):
                validated[k] = [str(x).strip() for x in raw_v if x is not None]
            else:
                validated[k] = str(raw_v).strip()

    return validated, unmapped


# ============================================================
# QUERY UNDERSTANDING
# ============================================================

class QueryUnderstanding:

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self.model = model or get_model_for_role("router")
        self.client = client or get_async_client()
        self._vocab = None

    def _get_vocab(self) -> Optional[Dict[str, List[str]]]:
        if self._vocab is None:
            try:
                from graph.graph_retriever import Neo4jGraphRetriever
                retriever = Neo4jGraphRetriever()
                try:
                    self._vocab = retriever.get_vocabulary()
                finally:
                    retriever.close()
            except Exception:
                self._vocab = {}
        return self._vocab

    def _build_system_prompt(self) -> str:
        return """
You are a Query Understanding module for a Test Management Graph RAG system.
Your job is ONLY to analyze the user's query and return valid JSON.

Do NOT answer the question. Do NOT retrieve data. Do NOT invent IDs or facts.

Return ONLY valid JSON with this exact structure:
{
    "intent": "testcase_lookup | execution_lookup | defect_lookup | testcase_execution_analysis | defect_analysis | failure_analysis | screenshot_lookup | semantic_search | general_test_analysis",
    "target_entity": "defect | test_case | execution | screenshot | requirement | module | unknown",
    "operation": "lookup | list | count | group_by | semantic",
    "group_by_field": null,
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": [],
        "screenshot_ids": []
    },
    "filters": {},
    "low_level_keywords": [],
    "high_level_keywords": []
}

------------------------------------------------------------
OPERATIONS:
- lookup: names an ID (e.g. "BUG-000176", "TC-000001", "EXEC-003016")
- list: asks to list or show matching items (e.g. "show all Critical defects")
- count: asks how many items match (e.g. "how many Failed executions in UAT")
- group_by: asks to group, aggregate, or top N by an attribute (e.g. "defects by severity", "top modules by defects")
- semantic: describes an issue in natural language without an exact ID or precise attribute (e.g. "login timeout crash")

------------------------------------------------------------
TARGET ENTITY:
Identify primary entity type: defect, test_case, execution, screenshot, requirement, module, or unknown.

------------------------------------------------------------
ENVIRONMENTS:
Real environments are DEV, UAT, QA, STAGING. (PROD does NOT exist).

------------------------------------------------------------
EXAMPLES:

Example 1 (Lookup):
Query: "Give me details about defect BUG-000176."
Result:
{
    "intent": "defect_lookup",
    "target_entity": "defect",
    "operation": "lookup",
    "group_by_field": null,
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": ["BUG-000176"],
        "screenshot_ids": []
    },
    "filters": {},
    "low_level_keywords": ["BUG-000176"],
    "high_level_keywords": ["defect details"]
}

Example 2 (List with filters):
Query: "Show all Critical defects in UAT."
Result:
{
    "intent": "defect_lookup",
    "target_entity": "defect",
    "operation": "list",
    "group_by_field": null,
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": [],
        "screenshot_ids": []
    },
    "filters": {
        "severity": "Critical",
        "environment": "UAT"
    },
    "low_level_keywords": ["Critical", "UAT"],
    "high_level_keywords": ["critical defects in UAT"]
}

Example 3 (Count with filters):
Query: "How many Failed executions in QA?"
Result:
{
    "intent": "failure_analysis",
    "target_entity": "execution",
    "operation": "count",
    "group_by_field": null,
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": [],
        "screenshot_ids": []
    },
    "filters": {
        "status": "Failed",
        "environment": "QA"
    },
    "low_level_keywords": ["Failed", "QA"],
    "high_level_keywords": ["failed executions in QA"]
}

Example 4 (Group by):
Query: "Defects grouped by severity"
Result:
{
    "intent": "defect_analysis",
    "target_entity": "defect",
    "operation": "group_by",
    "group_by_field": "severity",
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": [],
        "screenshot_ids": []
    },
    "filters": {},
    "low_level_keywords": ["severity"],
    "high_level_keywords": ["defects grouped by severity"]
}

Example 5 (Semantic):
Query: "Users experience timeout crash during payment checkout"
Result:
{
    "intent": "semantic_search",
    "target_entity": "defect",
    "operation": "semantic",
    "group_by_field": null,
    "limit": null,
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": [],
        "screenshot_ids": []
    },
    "filters": {},
    "low_level_keywords": ["timeout", "crash", "payment", "checkout"],
    "high_level_keywords": ["payment checkout timeout crash"]
}
""".strip()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        return tolerant_json_parse(text)

    def _validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            result = {}
        valid_targets = {"defect", "test_case", "execution", "screenshot", "requirement", "module", "unknown"}
        valid_ops = {"lookup", "list", "count", "group_by", "semantic"}

        if result.get("target_entity") not in valid_targets:
            result["target_entity"] = "unknown"
        if result.get("operation") not in valid_ops:
            result["operation"] = "semantic"

        if "entities" not in result or not isinstance(result["entities"], dict):
            result["entities"] = {}
        for k in ["test_case_ids", "execution_ids", "defect_ids", "screenshot_ids"]:
            if k not in result["entities"] or not isinstance(result["entities"][k], list):
                result["entities"][k] = []

        if not isinstance(result.get("filters"), dict):
            result["filters"] = {}
        if not isinstance(result.get("low_level_keywords"), list):
            result["low_level_keywords"] = []
        if not isinstance(result.get("high_level_keywords"), list):
            result["high_level_keywords"] = []

        return result

    def _fallback_parse(self, query: str) -> Dict[str, Any]:
        """Deterministic keyword-based fallback if LLM is unavailable or fails."""
        regex_ids = extract_regex_ids(query)
        q_lower = query.lower()

        # Target entity
        if regex_ids["defect_ids"]:
            target_entity = "defect"
        elif regex_ids["test_case_ids"]:
            target_entity = "test_case"
        elif regex_ids["execution_ids"]:
            target_entity = "execution"
        elif regex_ids["screenshot_ids"]:
            target_entity = "screenshot"
        elif any(w in q_lower for w in ["execution", "executions"]):
            target_entity = "execution"
        elif any(w in q_lower for w in ["test case", "testcase", "test cases", "testcases"]):
            target_entity = "test_case"
        elif any(w in q_lower for w in ["screenshot", "screenshots", "image"]):
            target_entity = "screenshot"
        elif any(w in q_lower for w in ["defect", "defects", "bug", "bugs", "issue", "crash", "error", "failure", "broken", "problem"]):
            target_entity = "defect"
        else:
            target_entity = "unknown"

        # Operation
        has_any_id = any(bool(v) for v in regex_ids.values())
        if has_any_id:
            op = "lookup"
        elif any(w in q_lower for w in ["by severity", "by status", "by module", "by priority", "grouped by", "top "]):
            op = "group_by"
        elif any(re.search(r"\b" + re.escape(w) + r"\b", q_lower) for w in ["how many", "count of", "total count", "number of", "count"]):
            op = "count"
        elif any(re.search(r"\b" + re.escape(w) + r"\b", q_lower) for w in ["show", "list", "filter"]):
            op = "list"
        else:
            op = "semantic"

        group_by_field = None
        if op == "group_by":
            for f in ["severity", "module", "status", "priority", "bug_type", "environment"]:
                if f in q_lower:
                    group_by_field = f
                    break

        intent = "semantic_search"
        if op in ("lookup", "list"):
            if target_entity == "defect":
                intent = "defect_lookup"
            elif target_entity == "test_case":
                intent = "testcase_lookup"
            elif target_entity == "execution":
                intent = "execution_lookup"
            elif target_entity == "screenshot":
                intent = "screenshot_lookup"
        elif op in ("group_by", "count"):
            if target_entity == "defect":
                intent = "defect_analysis"
            elif target_entity == "execution":
                intent = "failure_analysis"
            else:
                intent = "general_test_analysis"

        # Basic filter extraction
        raw_filters = {}
        for sev in ["critical", "blocker", "major", "minor"]:
            if sev in q_lower:
                raw_filters["severity"] = sev.capitalize()
        for env in ["dev", "uat", "qa", "staging"]:
            if f"in {env}" in q_lower or f" {env} " in q_lower:
                raw_filters["environment"] = env.upper()

        vocab = self._get_vocab()
        for mod in vocab.get("modules", []):
            if mod.lower() in q_lower:
                raw_filters["module"] = mod
                break
        for st in vocab.get("statuses", []):
            if st.lower() in q_lower:
                raw_filters["status"] = st
                break

        validated_filters, unmapped = validate_and_map_filters(raw_filters, vocab)

        words = [w for w in re.findall(r"\b\w+\b", q_lower) if len(w) > 3]

        return {
            "intent": intent,
            "target_entity": target_entity,
            "operation": op,
            "group_by_field": group_by_field,
            "limit": None,
            "entities": regex_ids,
            "filters": validated_filters,
            "unmapped_filters": unmapped,
            "low_level_keywords": words[:5],
            "high_level_keywords": [query.strip()],
            "understanding_fallback": True,
        }

    async def analyze(
        self,
        query: str,
        max_retries: int = 3,
        base_backoff: float = 2.0
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        # 1. Deterministic regex extraction (always runs and augments)
        regex_ids = extract_regex_ids(query)

        # 2. Call LLM with retry & exponential backoff on HTTP 429 / 5xx / timeouts
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": query},
        ]
        try:
            content = await complete_chat(
                messages=messages,
                role="router",
                temperature=0,
                max_retries=max_retries,
                base_backoff=base_backoff,
                client=self.client,
                model=self.model,
            )
            parsed = self._extract_json(content)
            result = self._validate_result(parsed)
        except LLMInfraError as e:
            print(
                f"[QUERY UNDERSTANDING FAILURE] Infrastructure error persisted after {max_retries} attempts: {e}"
            )
            return {
                "status": "infra_error",
                "intent": "infra_error",
                "target_entity": "unknown",
                "operation": "unknown",
                "group_by_field": None,
                "limit": None,
                "entities": regex_ids,
                "filters": {},
                "unmapped_filters": [],
                "low_level_keywords": [],
                "high_level_keywords": [query.strip()],
                "understanding_fallback": False,
                "error": f"Infrastructure error after {max_retries} attempts: {e}",
            }
        except Exception as e:
            # Non-transient parsing/extraction error: use fallback parse
            print(f"[QUERY UNDERSTANDING WARNING] Non-transient error: {e}. Falling back to rule-based parse.")
            return self._fallback_parse(query)

        if result is None:
            return self._fallback_parse(query)

        # 2. Augment and override entities with deterministic regex
        for k, v in regex_ids.items():
            combined = list(dict.fromkeys(v + result["entities"].get(k, [])))
            result["entities"][k] = combined

        # If IDs exist, enforce operation=lookup
        if any(bool(result["entities"][k]) for k in ["defect_ids", "test_case_ids", "execution_ids", "screenshot_ids"]):
            result["operation"] = "lookup"
            if result["entities"]["defect_ids"] and result["target_entity"] == "unknown":
                result["target_entity"] = "defect"
            elif result["entities"]["test_case_ids"] and result["target_entity"] == "unknown":
                result["target_entity"] = "test_case"
            elif result["entities"]["execution_ids"] and result["target_entity"] == "unknown":
                result["target_entity"] = "execution"
            elif result["entities"]["screenshot_ids"] and result["target_entity"] == "unknown":
                result["target_entity"] = "screenshot"

        # 3. Vocabulary validation
        vocab = self._get_vocab()
        validated_filters, unmapped = validate_and_map_filters(result["filters"], vocab)
        result["filters"] = validated_filters
        result["unmapped_filters"] = unmapped
        result["understanding_fallback"] = False

        return result