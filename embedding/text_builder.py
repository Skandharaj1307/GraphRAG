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
    Convert a Defect record into semantic text
    suitable for embedding.
    """

    return f"""
Defect ID: {row.get('defect_id', '')}

Title:
{row.get('title', '')}

Description:
{row.get('description', '')}

Module: {row.get('module', '')}

Severity: {row.get('severity', '')}
Priority: {row.get('priority', '')}

Status: {row.get('status', '')}

Root Cause:
{row.get('root_cause', '')}

Bug Type: {row.get('bug_type', '')}

Reproducibility:
{row.get('reproducibility', '')}

Environment:
{row.get('environment', '')}

Regression:
{row.get('regression', '')}

Comments:
{row.get('comments', '')}

Fix Version:
{row.get('fix_version', '')}
""".strip()