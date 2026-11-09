import re


def extract_error_signature(text: str) -> str:
    """
    Extract exception names, error types, and failure signatures from text.
    Matches patterns like AccessError, ValueError, NullPointerException,
    'permission error', 'validation exception', etc.
    """
    if not text or not isinstance(text, str):
        return ""

    patterns = [
        r'\b[A-Z][a-zA-Z0-9]*(?:Error|Exception|Fault|Failure)\b',
        r'\b(?:permission error|validation exception|timeout error|connection refused|syntax error|null pointer)\b',
    ]
    signatures = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip()
            if cleaned and cleaned not in signatures:
                signatures.append(cleaned)
    return ", ".join(signatures)


def build_testcase_text(row):
    """
    Convert a TestCase record into semantic text
    suitable for embedding.
    """

    return f"""
Test Case ID: {row.get('test_case_id', '')}

Requirement: {row.get('requirement_id', '')}
Epic: {row.get('epic', '')}
Story: {row.get('story', '')}

Module: {row.get('module', '')}
Submodule: {row.get('submodule', '')}
Feature: {row.get('feature', '')}
Component: {row.get('component', '')}

Priority: {row.get('priority', '')}
Severity: {row.get('severity', '')}
Risk: {row.get('risk', '')}

Precondition:
{row.get('precondition', '')}

Test Steps:
{row.get('test_steps', '')}

Expected Result:
{row.get('expected_result', '')}

Actual Result:
{row.get('actual_result', '')}

Acceptance Criteria:
{row.get('acceptance_criteria', '')}
""".strip()


def build_defect_text(row):
    """
    Convert a Defect record into semantic text suitable for embedding.
    Enriched with root cause, linked test steps, and error signature.
    """
    root_cause = row.get('root_cause', '') or ''
    linked_steps = row.get('test_steps', '') or row.get('linked_test_step', '') or ''

    # Error signature: explicit property, or extracted from execution_notes / description
    error_sig = row.get('error_signature', '') or ''
    if not error_sig:
        notes = row.get('execution_notes', '') or ''
        desc = row.get('description', '') or ''
        extracted = []
        if notes:
            sig_from_notes = extract_error_signature(notes)
            if sig_from_notes:
                extracted.append(sig_from_notes)
            else:
                extracted.append(notes.strip())
        if desc:
            sig_from_desc = extract_error_signature(desc)
            if sig_from_desc and sig_from_desc not in extracted:
                extracted.append(sig_from_desc)
        error_sig = "; ".join(extracted)

    sections = [
        f"Defect ID: {row.get('defect_id', '')}",
        f"Title:\n{row.get('title', '')}",
        f"Description:\n{row.get('description', '')}",
        f"Module: {row.get('module', '')}",
        f"Severity: {row.get('severity', '')}",
        f"Priority: {row.get('priority', '')}",
        f"Status: {row.get('status', '')}",
        f"Root Cause:\n{root_cause}",
        f"Bug Type: {row.get('bug_type', '')}",
        f"Reproducibility:\n{row.get('reproducibility', '')}",
        f"Environment:\n{row.get('environment', '')}",
        f"Regression:\n{row.get('regression', '')}",
    ]

    if linked_steps:
        sections.append(f"Linked Test Steps:\n{linked_steps}")

    if error_sig:
        sections.append(f"Error Signature:\n{error_sig}")

    sections.extend([
        f"Comments:\n{row.get('comments', '')}",
        f"Fix Version:\n{row.get('fix_version', '')}",
    ])

    return "\n\n".join(s for s in sections if s.strip()).strip()
