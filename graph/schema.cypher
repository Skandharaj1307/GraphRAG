// ==============================
// Test Management Graph Schema
// ==============================

// TestCase → Execution
// A test case can have many executions.

// TestCase → Defect
// A test case can be associated with defects.

// Execution → Defect
// An execution can discover a defect.


// Node types:
//
// TestCase
// Execution
// Defect


// Relationships:
//
// (:TestCase)-[:HAS_EXECUTION]->(:Execution)
//
// (:TestCase)-[:HAS_DEFECT]->(:Defect)
//
// (:Execution)-[:FOUND_DEFECT]->(:Defect)