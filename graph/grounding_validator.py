import re
from typing import Dict, Any, List, Tuple


# ============================================================
# GROUNDING VALIDATOR
# ============================================================

class GroundingValidator:

    """
    Deterministic post-generation validator.

    This validator does NOT call an LLM.

    It checks whether a generated answer is consistent with
    the evidence supplied by the GraphRAG pipeline.
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        # ----------------------------------------------------
        # Supported GraphRAG entity ID formats
        # ----------------------------------------------------

        self.id_pattern = re.compile(
            r"\b(?:TC|EXEC|BUG|SCR)-\d{6,}\b",
            re.IGNORECASE
        )

        # ----------------------------------------------------
        # Supported relationship names
        # ----------------------------------------------------

        self.relationship_pattern = re.compile(
            r"\b(?:HAS_EXECUTION|HAS_DEFECT|FOUND_DEFECT|"
            r"HAS_SCREENSHOT|CAPTURED_SCREENSHOT)\b",
            re.IGNORECASE
        )

    # ========================================================
    # EXTRACT IDS
    # ========================================================

    def extract_ids(
        self,
        text: str
    ) -> List[str]:

        """
        Extract entity IDs from generated text.
        """

        matches = self.id_pattern.findall(text)

        unique_ids = []

        for item in matches:

            normalized = item.upper()

            if normalized not in unique_ids:

                unique_ids.append(
                    normalized
                )

        return unique_ids

    # ========================================================
    # EXTRACT RELATIONSHIPS
    # ========================================================

    def extract_relationship_names(
        self,
        text: str
    ) -> List[str]:

        """
        Extract known GraphRAG relationship names from
        generated text.
        """

        matches = self.relationship_pattern.findall(
            text
        )

        unique_relationships = []

        for item in matches:

            normalized = item.upper()

            if normalized not in unique_relationships:

                unique_relationships.append(
                    normalized
                )

        return unique_relationships

    # ========================================================
    # GET EVIDENCE IDS
    # ========================================================

    def get_evidence_ids(
        self,
        context: Dict[str, Any]
    ) -> List[str]:

        """
        Extract all known entity IDs from the assembled
        GraphRAG context.
        """

        evidence_ids = []

        # ----------------------------------------------------
        # Entities
        # ----------------------------------------------------

        for entity in context.get(
            "entities",
            []
        ):

            entity_id = entity.get("id")

            if entity_id:

                normalized = str(
                    entity_id
                ).upper()

                if normalized not in evidence_ids:

                    evidence_ids.append(
                        normalized
                    )

        # ----------------------------------------------------
        # Relationships
        # ----------------------------------------------------

        for relationship in context.get(
            "relationships",
            []
        ):

            source_id = relationship.get(
                "source_id"
            )

            target_id = relationship.get(
                "target_id"
            )

            for entity_id in (
                source_id,
                target_id
            ):

                if entity_id:

                    normalized = str(
                        entity_id
                    ).upper()

                    if normalized not in evidence_ids:

                        evidence_ids.append(
                            normalized
                        )

        # ----------------------------------------------------
        # Screenshots
        # ----------------------------------------------------

        for screenshot in context.get(
            "screenshots",
            []
        ):

            screenshot_id = screenshot.get(
                "id"
            )

            if screenshot_id:

                normalized = str(
                    screenshot_id
                ).upper()

                if normalized not in evidence_ids:

                    evidence_ids.append(
                        normalized
                    )

            # ----------------------------------------------
            # Source metadata
            # ----------------------------------------------

            source_metadata = screenshot.get(
                "source_metadata",
                {}
            )

            for value in source_metadata.values():

                if value:

                    normalized = str(
                        value
                    ).upper()

                    if normalized not in evidence_ids:

                        evidence_ids.append(
                            normalized
                        )

            # ----------------------------------------------
            # Graph linkage
            # ----------------------------------------------

            graph_linkage = screenshot.get(
                "graph_linkage",
                {}
            )

            for key, value in graph_linkage.items():

                if isinstance(value, list):

                    for item in value:

                        normalized = str(
                            item
                        ).upper()

                        if normalized not in evidence_ids:

                            evidence_ids.append(
                                normalized
                            )

                elif value:

                    normalized = str(
                        value
                    ).upper()

                    if normalized not in evidence_ids:

                        evidence_ids.append(
                            normalized
                        )

        return evidence_ids

    # ========================================================
    # GET AUTHORITATIVE RELATIONSHIPS
    # ========================================================

    def get_authoritative_relationships(
        self,
        context: Dict[str, Any]
    ) -> List[Tuple[str, str, str]]:

        """
        Extract authoritative Neo4j relationships.

        ContextAssembler places structured graph relationships
        in the relationships section.
        """

        relationships = []

        for relationship in context.get(
            "relationships",
            []
        ):

            source_id = relationship.get(
                "source_id"
            )

            target_id = relationship.get(
                "target_id"
            )

            relationship_type = relationship.get(
                "relationship"
            )

            if (
                source_id
                and target_id
                and relationship_type
            ):

                relationships.append(
                    (
                        str(source_id).upper(),
                        str(target_id).upper(),
                        str(
                            relationship_type
                        ).upper()
                    )
                )

        return relationships

    # ========================================================
    # VALIDATE IDS
    # ========================================================

    def validate_ids(
        self,
        answer: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:

        """
        Check whether IDs mentioned in the answer are present
        in the retrieved evidence.
        """

        answer_ids = self.extract_ids(
            answer
        )

        evidence_ids = self.get_evidence_ids(
            context
        )

        unsupported_ids = [
            item
            for item in answer_ids
            if item not in evidence_ids
        ]

        return (
            len(unsupported_ids) == 0,
            unsupported_ids
        )

    # ========================================================
    # VALIDATE RELATIONSHIP NAMES
    # ========================================================

    def validate_relationship_names(
        self,
        answer: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:

        """
        Check explicit relationship names appearing in the
        answer against relationships present in the evidence.
        """

        answer_relationships = (
            self.extract_relationship_names(
                answer
            )
        )

        evidence_relationships = [
            relationship_type
            for _, _, relationship_type
            in self.get_authoritative_relationships(
                context
            )
        ]

        unsupported_relationships = [
            item
            for item in answer_relationships
            if item not in evidence_relationships
        ]

        return (
            len(
                unsupported_relationships
            ) == 0,
            unsupported_relationships
        )

    # ========================================================
    # VALIDATE AUTHORITATIVE LINKS
    # ========================================================

    def validate_authoritative_links(
        self,
        answer: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:

        """
        Detect explicit graph relationship expressions
        in the generated answer and verify them against
        authoritative Neo4j relationships.

        Example:

            TC-000001 --HAS_DEFECT--> BUG-000176

        is checked against the retrieved graph.
        """

        relationships = (
            self.get_authoritative_relationships(
                context
            )
        )

        warnings = []

        # ----------------------------------------------------
        # Match explicit relationship expressions
        #
        # Example:
        #
        # TC-000001 --HAS_DEFECT--> BUG-000176
        #
        # The relationship name is captured dynamically.
        # ----------------------------------------------------

        arrow_pattern = re.compile(
            r"\b"
            r"((?:TC|EXEC|BUG|SCR)-\d{6,})"
            r"\s*"
            r"--\s*"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*-->\s*"
            r"((?:TC|EXEC|BUG|SCR)-\d{6,})"
            r"\b",
            re.IGNORECASE
        )

        for match in arrow_pattern.finditer(
            answer
        ):

            source_id = match.group(1).upper()

            relationship_type = (
                match.group(2).upper()
            )

            target_id = match.group(3).upper()

            # ------------------------------------------------
            # Check exact:
            #
            # source + relationship + target
            # ------------------------------------------------

            exists = any(
                source == source_id
                and target == target_id
                and relationship == relationship_type
                for source, target, relationship
                in relationships
            )

            if not exists:

                warnings.append(
                    "Unsupported graph relationship: "
                    f"{source_id} "
                    f"--{relationship_type}--> "
                    f"{target_id}"
                )

        # ----------------------------------------------------
        # Simple arrow syntax
        #
        # Example:
        #
        # TC-000001 -> BUG-000176
        #
        # No relationship type is available, so only the
        # source-target pair is checked.
        # ----------------------------------------------------

        simple_arrow_pattern = re.compile(
            r"\b"
            r"((?:TC|EXEC|BUG|SCR)-\d{6,})"
            r"\s*(?:->|→)\s*"
            r"((?:TC|EXEC|BUG|SCR)-\d{6,})"
            r"\b",
            re.IGNORECASE
        )

        for match in simple_arrow_pattern.finditer(
            answer
        ):

            source_id = match.group(1).upper()

            target_id = match.group(2).upper()

            exists = any(
                source == source_id
                and target == target_id
                for source, target, _
                in relationships
            )

            if not exists:

                warnings.append(
                    "Unsupported graph relationship: "
                    f"{source_id} -> {target_id}"
                )

        return (
            len(warnings) == 0,
            warnings
        )

    # ========================================================
    # SCREENSHOT CONSISTENCY
    # ========================================================

    def get_inconsistent_screenshots(
        self,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        """
        Return screenshots whose source metadata conflicts
        with authoritative graph linkage.
        """

        inconsistent = []

        for screenshot in context.get(
            "screenshots",
            []
        ):

            if (
                screenshot.get(
                    "metadata_consistent"
                )
                is False
            ):

                inconsistent.append(
                    screenshot
                )

        return inconsistent

    # ========================================================
    # FULL VALIDATION
    # ========================================================

    def validate(
        self,
        answer: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:

        """
        Run all deterministic grounding checks.
        """

        # ----------------------------------------------------
        # Basic answer validation
        # ----------------------------------------------------

        if not answer or not answer.strip():

            return {
                "valid": False,
                "errors": [
                    "Generated answer is empty."
                ],
                "warnings": [],
                "answer_ids": [],
                "unsupported_ids": [],
                "inconsistent_screenshot_count": 0
            }

        # ----------------------------------------------------
        # ID validation
        # ----------------------------------------------------

        ids_valid, unsupported_ids = (
            self.validate_ids(
                answer,
                context
            )
        )

        # ----------------------------------------------------
        # Relationship-name validation
        # ----------------------------------------------------

        relationships_valid, unsupported_relationships = (
            self.validate_relationship_names(
                answer,
                context
            )
        )

        # ----------------------------------------------------
        # Exact relationship validation
        # ----------------------------------------------------

        links_valid, link_warnings = (
            self.validate_authoritative_links(
                answer,
                context
            )
        )

        # ----------------------------------------------------
        # Screenshot warnings
        # ----------------------------------------------------

        inconsistent_screenshots = (
            self.get_inconsistent_screenshots(
                context
            )
        )

        warnings = []

        if inconsistent_screenshots:

            warnings.append(
                f"{len(inconsistent_screenshots)} "
                "screenshot(s) contain metadata that "
                "conflicts with authoritative graph linkage."
            )

        warnings.extend(
            link_warnings
        )

        # ----------------------------------------------------
        # Errors
        # ----------------------------------------------------

        errors = []

        if unsupported_ids:

            errors.append(
                "Answer contains IDs that were not found "
                "in the retrieved evidence: "
                + ", ".join(
                    unsupported_ids
                )
            )

        if unsupported_relationships:

            errors.append(
                "Answer contains relationship types that "
                "were not found in the retrieved evidence: "
                + ", ".join(
                    unsupported_relationships
                )
            )

        if link_warnings:

            errors.extend(
                link_warnings
            )

        # ----------------------------------------------------
        # Final validation result
        # ----------------------------------------------------

        valid = (
            ids_valid
            and relationships_valid
            and links_valid
            and len(errors) == 0
        )

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "answer_ids": self.extract_ids(
                answer
            ),
            "unsupported_ids": unsupported_ids,
            "inconsistent_screenshot_count": len(
                inconsistent_screenshots
            )
        }


# ============================================================
# LOCAL TEST
# ============================================================

def main():

    print("=" * 60)
    print("PART 6.5 - GROUNDING / HALLUCINATION SAFEGUARDS")
    print("=" * 60)

    # --------------------------------------------------------
    # Test context
    # --------------------------------------------------------

    context = {

        "entities": [
            {
                "id": "TC-000001",
                "type": "TestCase"
            },
            {
                "id": "EXEC-003016",
                "type": "Execution"
            },
            {
                "id": "BUG-000176",
                "type": "Defect"
            },
            {
                "id": "BUG-009797",
                "type": "Defect"
            }
        ],

        "relationships": [
            {
                "source_id": "TC-000001",
                "target_id": "EXEC-003016",
                "relationship": "HAS_EXECUTION"
            },
            {
                "source_id": "TC-000001",
                "target_id": "BUG-000176",
                "relationship": "HAS_DEFECT"
            },
            {
                "source_id": "EXEC-003016",
                "target_id": "BUG-000176",
                "relationship": "FOUND_DEFECT"
            },
            {
                "source_id": "TC-000001",
                "target_id": "BUG-009797",
                "relationship": "HAS_DEFECT"
            },
            {
                "source_id": "EXEC-003016",
                "target_id": "BUG-009797",
                "relationship": "FOUND_DEFECT"
            }
        ],

        "screenshots": [
            {
                "id": "SCR-ocr_batch_009-0935",

                "metadata_consistent": False,

                "source_metadata": {
                    "test_case_id": "TC-007094",
                    "execution_id": "EXEC-019839",
                    "defect_id": "BUG-000176"
                },

                "graph_linkage": {
                    "test_case_ids": [
                        "TC-000001"
                    ],
                    "execution_ids": [
                        "EXEC-003016"
                    ],
                    "defect_id": "BUG-000176"
                }
            }
        ]
    }

    validator = GroundingValidator()

    # ========================================================
    # TEST 1
    # ========================================================

    valid_answer = (
        "The execution EXEC-003016 found two defects: "
        "BUG-000176 and BUG-009797."
    )

    result = validator.validate(
        valid_answer,
        context
    )

    print()
    print("TEST 1 - VALID GROUNDED ANSWER")

    print(
        f"  Valid: {result['valid']}"
    )

    print(
        f"  Answer IDs: {result['answer_ids']}"
    )

    assert result["valid"] is True

    print(
        "  ✓ Passed"
    )

    # ========================================================
    # TEST 2
    # ========================================================

    hallucinated_answer = (
        "The execution found BUG-000176, "
        "BUG-009797 and BUG-123456."
    )

    result = validator.validate(
        hallucinated_answer,
        context
    )

    print()
    print("TEST 2 - HALLUCINATED ID")

    print(
        f"  Valid: {result['valid']}"
    )

    print(
        f"  Unsupported IDs: "
        f"{result['unsupported_ids']}"
    )

    assert result["valid"] is False

    assert (
        "BUG-123456"
        in result["unsupported_ids"]
    )

    print(
        "  ✓ Hallucinated ID detected"
    )

    # ========================================================
    # TEST 3
    # ========================================================

    relationship_answer = (
        "TC-000001 --CREATED_DEFECT--> BUG-000176"
    )

    result = validator.validate(
        relationship_answer,
        context
    )

    print()
    print("TEST 3 - UNSUPPORTED RELATIONSHIP")

    print(
        f"  Valid: {result['valid']}"
    )

    print(
        f"  Errors: {result['errors']}"
    )

    assert result["valid"] is False

    assert any(
        "CREATED_DEFECT"
        in error
        for error in result["errors"]
    )

    print(
        "  ✓ Unsupported relationship detected"
    )

    # ========================================================
    # TEST 4
    # ========================================================

    normal_answer = (
        "BUG-000176 was found in EXEC-003016."
    )

    result = validator.validate(
        normal_answer,
        context
    )

    print()
    print("TEST 4 - SCREENSHOT CONSISTENCY")

    print(
        f"  Valid: {result['valid']}"
    )

    print(
        f"  Inconsistent screenshots: "
        f"{result['inconsistent_screenshot_count']}"
    )

    assert (
        result["inconsistent_screenshot_count"]
        == 1
    )

    assert len(
        result["warnings"]
    ) > 0

    print(
        "  ✓ Screenshot conflict detected"
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("=" * 60)
    print("✓ GROUNDING VALIDATOR TEST PASSED")
    print("=" * 60)

    print()
    print(
        "No Mistral API request was made."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()