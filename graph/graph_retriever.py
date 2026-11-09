

import os
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase

try:
    from graph.local_secrets import NEO4J_PASSWORD as _DEFAULT_NEO4J_PASSWORD
except ImportError:
    _DEFAULT_NEO4J_PASSWORD = ""

from graph.retrieval_config import (
    NEO4J_URI as _DEFAULT_NEO4J_URI,
    NEO4J_USER as _DEFAULT_NEO4J_USER,
    NEO4J_DATABASE as _DEFAULT_NEO4J_DATABASE,
    DEFAULT_LIMIT,
    MAX_PATHS,
    FULLTEXT_INDEX,
    VECTOR_INDEXES,
)


def _clean_props(p: Any) -> Any:
    """Return a copy of properties map or list without embedding/embedding_model."""
    if p is None:
        return None
    if isinstance(p, dict):
        return {
            k: _clean_props(v) for k, v in p.items()
            if k not in ("embedding", "embedding_model")
        }
    if isinstance(p, list):
        return [_clean_props(x) for x in p]
    return p


class Neo4jGraphRetriever:

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", _DEFAULT_NEO4J_URI)
        self.username = username or os.getenv("NEO4J_USER", _DEFAULT_NEO4J_USER)
        self.password = password or os.getenv("NEO4J_PASSWORD", _DEFAULT_NEO4J_PASSWORD)
        self.database = database or os.getenv("NEO4J_DATABASE", _DEFAULT_NEO4J_DATABASE)

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )

        self.has_modules = False
        self.has_environments = False
        self.indexes = {}
        self.has_fulltext = False
        self._vector_labels = set()
        self._vocabulary_cache = None

        self._detect_capabilities()

    def _session(self):
        """Return a session targeting the configured database."""
        return self.driver.session(database=self.database)

    def _detect_capabilities(self):
        """Inspect schema capabilities once at initialization."""
        try:
            with self._session() as session:
                res = session.run("MATCH (m:Module) RETURN count(m) > 0 AS has_m LIMIT 1", {})
                rec = res.single()
                self.has_modules = bool(rec and rec["has_m"])
        except Exception:
            self.has_modules = False

        try:
            with self._session() as session:
                res = session.run("MATCH (e:Environment) RETURN count(e) > 0 AS has_e LIMIT 1", {})
                rec = res.single()
                self.has_environments = bool(rec and rec["has_e"])
        except Exception:
            self.has_environments = False

        try:
            with self._session() as session:
                res = session.run("SHOW INDEXES YIELD name, type, state, labelsOrTypes", {})
                for row in res:
                    name = row.get("name")
                    idx_type = row.get("type")
                    state = row.get("state")
                    labels = row.get("labelsOrTypes")
                    self.indexes[name] = {
                        "type": idx_type,
                        "state": state,
                        "labels": labels,
                    }
                    if name == FULLTEXT_INDEX and state == "ONLINE":
                        self.has_fulltext = True
                    if idx_type == "VECTOR" and state == "ONLINE" and labels:
                        for lbl in labels:
                            self._vector_labels.add(lbl.lower())
        except Exception:
            pass

    def has_vector(self, label: str) -> bool:
        """Check if vector index for the given label/entity is ONLINE."""
        norm = label.lower().replace("_", "")
        for entity_key, idx_name in VECTOR_INDEXES.items():
            if norm == entity_key.replace("_", ""):
                idx_info = self.indexes.get(idx_name)
                if idx_info and idx_info.get("state") == "ONLINE":
                    return True
        for lbl in self._vector_labels:
            if norm == lbl.replace("_", ""):
                return True
        return False

    def close(self):
        self.driver.close()

    # ---------------------------------------------------------
    # Connection Test
    # ---------------------------------------------------------

    def test_connection(self) -> bool:
        try:
            with self._session() as session:
                result = session.run("RETURN 1 AS result", {})
                record = result.single()
                if record and record["result"] == 1:
                    return True
                return False
        except Exception as e:
            raise RuntimeError(
                f"Neo4j connection test failed on database '{self.database}': {e}"
            ) from e

    # ---------------------------------------------------------
    # Single Node Lookups
    # ---------------------------------------------------------

    def get_testcase(self, test_case_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (t:TestCase {test_case_id: $id})
        RETURN properties(t) AS testcase
        """
        with self._session() as session:
            result = session.run(cypher, {"id": test_case_id})
            record = result.single()
            if record is None or record["testcase"] is None:
                return None
            return _clean_props(record["testcase"])

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (e:Execution {execution_id: $id})
        RETURN properties(e) AS execution
        """
        with self._session() as session:
            result = session.run(cypher, {"id": execution_id})
            record = result.single()
            if record is None or record["execution"] is None:
                return None
            return _clean_props(record["execution"])

    def get_defect(self, defect_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (d:Defect {defect_id: $id})
        RETURN properties(d) AS defect
        """
        with self._session() as session:
            result = session.run(cypher, {"id": defect_id})
            record = result.single()
            if record is None or record["defect"] is None:
                return None
            return _clean_props(record["defect"])

    def get_screenshot(self, screenshot_id: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (s:Screenshot {screenshot_id: $id})
        RETURN properties(s) AS screenshot
        """
        with self._session() as session:
            result = session.run(cypher, {"id": screenshot_id})
            record = result.single()
            if record is None or record["screenshot"] is None:
                return None
            return _clean_props(record["screenshot"])

    # ---------------------------------------------------------
    # Multi-hop Path Retrievals (OPTIONAL MATCH)
    # ---------------------------------------------------------

    def get_testcase_execution_defects(
        self,
        test_case_id: str,
        limit: int = MAX_PATHS,
    ) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (t:TestCase {test_case_id: $id})
        OPTIONAL MATCH (t)-[:HAS_EXECUTION]->(e:Execution)
        OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d:Defect)
        RETURN properties(t) AS testcase,
               properties(e) AS execution,
               properties(d) AS defect
        ORDER BY e.execution_id, d.defect_id
        LIMIT $limit
        """
        with self._session() as session:
            result = session.run(cypher, {"id": test_case_id, "limit": limit})
            records = []
            for record in result:
                records.append({
                    "testcase": _clean_props(record["testcase"]),
                    "execution": _clean_props(record["execution"]),
                    "defect": _clean_props(record["defect"]),
                })
            return records

    def get_full_testcase_context(
        self,
        test_case_id: str,
        limit: int = MAX_PATHS,
    ) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (t:TestCase {test_case_id: $id})
        OPTIONAL MATCH (t)-[:HAS_EXECUTION]->(e:Execution)
        OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d:Defect)
        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s:Screenshot)
        RETURN properties(t) AS testcase,
               properties(e) AS execution,
               properties(d) AS defect,
               properties(s) AS screenshot
        ORDER BY e.execution_id, d.defect_id, s.screenshot_id
        LIMIT $limit
        """
        with self._session() as session:
            result = session.run(cypher, {"id": test_case_id, "limit": limit})
            records = []
            for record in result:
                records.append({
                    "testcase": _clean_props(record["testcase"]),
                    "execution": _clean_props(record["execution"]),
                    "defect": _clean_props(record["defect"]),
                    "screenshot": _clean_props(record["screenshot"]),
                })
            return records

    def get_full_defect_context(
        self,
        defect_id: str,
        limit: int = 20,
    ) -> Optional[Dict[str, Any]]:
        # 2-hop ego expansion: Defect <-> Execution <-> TestCase (and Screenshot)
        cypher = """
        MATCH (d:Defect {defect_id: $id})
        OPTIONAL MATCH (e:Execution)-[:FOUND_DEFECT]->(d)
        OPTIONAL MATCH (t_direct:TestCase)-[:HAS_DEFECT]->(d)
        OPTIONAL MATCH (t_exec:TestCase)-[:HAS_EXECUTION]->(e)
        WITH d, e, collect(DISTINCT t_direct) + collect(DISTINCT t_exec) AS all_tcs
        UNWIND (CASE WHEN size(all_tcs) > 0 THEN all_tcs ELSE [null] END) AS t
        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s_def:Screenshot)
        OPTIONAL MATCH (e)-[:CAPTURED_SCREENSHOT]->(s_exec:Screenshot)
        OPTIONAL MATCH (t)-[:HAS_SCREENSHOT]->(s_tc:Screenshot)
        OPTIONAL MATCH (e)-[:HAS_FAILURE_LOG]->(lc:LogChunk)
        WITH d,
             collect(DISTINCT properties(e))[..$limit] AS executions,
             collect(DISTINCT properties(t))[..$limit] AS testcases,
             (collect(DISTINCT properties(s_def)) + collect(DISTINCT properties(s_exec)) + collect(DISTINCT properties(s_tc)))[..$limit] AS screenshots,
             collect(DISTINCT properties(lc))[..$limit] AS failure_logs
        RETURN properties(d) AS defect,
               executions,
               testcases,
               screenshots,
               failure_logs
        """
        with self._session() as session:
            result = session.run(cypher, {"id": defect_id, "limit": limit})
            record = result.single()
            if record is None or record["defect"] is None:
                return None
            executions = [_clean_props(e) for e in record["executions"] if e is not None]
            testcases = [_clean_props(t) for t in record["testcases"] if t is not None]
            screenshots = [_clean_props(s) for s in record["screenshots"] if s is not None]
            failure_logs = [_clean_props(l) for l in record.get("failure_logs", []) if l is not None]
            primary_execution = executions[0] if executions else None
            primary_testcase = testcases[0] if testcases else None
            primary_failure_log = failure_logs[0] if failure_logs else None
            return {
                "defect": _clean_props(record["defect"]),
                "execution": primary_execution,
                "testcase": primary_testcase,
                "failure_log": primary_failure_log,
                "executions": executions,
                "testcases": testcases,
                "screenshots": screenshots,
                "failure_logs": failure_logs,
            }

    def get_execution_context(
        self,
        execution_id: str,
        limit: int = 20,
    ) -> Optional[Dict[str, Any]]:
        # 2-hop ego expansion: Execution <-> TestCase <-> Defect (and Screenshot)
        cypher = """
        MATCH (e:Execution {execution_id: $id})
        OPTIONAL MATCH (t:TestCase)-[:HAS_EXECUTION]->(e)
        OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d_found:Defect)
        OPTIONAL MATCH (t)-[:HAS_DEFECT]->(d_tc:Defect)
        WITH e, t, collect(DISTINCT d_found) + collect(DISTINCT d_tc) AS all_defs
        UNWIND (CASE WHEN size(all_defs) > 0 THEN all_defs ELSE [null] END) AS d
        OPTIONAL MATCH (e)-[:CAPTURED_SCREENSHOT]->(s_exec:Screenshot)
        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s_def:Screenshot)
        OPTIONAL MATCH (t)-[:HAS_SCREENSHOT]->(s_tc:Screenshot)
        OPTIONAL MATCH (e)-[:HAS_FAILURE_LOG]->(lc:LogChunk)
        WITH e,
             collect(DISTINCT properties(t))[..$limit] AS testcases,
             collect(DISTINCT properties(d))[..$limit] AS defects,
             (collect(DISTINCT properties(s_exec)) + collect(DISTINCT properties(s_def)) + collect(DISTINCT properties(s_tc)))[..$limit] AS screenshots,
             collect(DISTINCT properties(lc))[..$limit] AS failure_logs
        RETURN properties(e) AS execution,
               testcases,
               defects,
               screenshots,
               failure_logs
        """
        with self._session() as session:
            result = session.run(cypher, {"id": execution_id, "limit": limit})
            record = result.single()
            if record is None or record["execution"] is None:
                return None
            testcases = [_clean_props(t) for t in record["testcases"] if t is not None]
            defects = [_clean_props(d) for d in record["defects"] if d is not None]
            screenshots = [_clean_props(s) for s in record["screenshots"] if s is not None]
            failure_logs = [_clean_props(l) for l in record.get("failure_logs", []) if l is not None]
            primary_testcase = testcases[0] if testcases else None
            primary_defect = defects[0] if defects else None
            primary_failure_log = failure_logs[0] if failure_logs else None
            return {
                "execution": _clean_props(record["execution"]),
                "testcase": primary_testcase,
                "defect": primary_defect,
                "failure_log": primary_failure_log,
                "testcases": testcases,
                "defects": defects,
                "screenshots": screenshots,
                "failure_logs": failure_logs,
            }

    def get_testcase_context(
        self,
        test_case_id: str,
        limit: int = 20,
    ) -> Optional[Dict[str, Any]]:
        # 2-hop ego expansion: TestCase <-> Execution <-> Defect (and Screenshot, LogChunk)
        cypher = """
        MATCH (t:TestCase {test_case_id: $id})
        OPTIONAL MATCH (t)-[:HAS_EXECUTION]->(e:Execution)
        OPTIONAL MATCH (t)-[:HAS_DEFECT]->(d_direct:Defect)
        OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d_exec:Defect)
        WITH t, e, collect(DISTINCT d_direct) + collect(DISTINCT d_exec) AS all_defs
        UNWIND (CASE WHEN size(all_defs) > 0 THEN all_defs ELSE [null] END) AS d
        OPTIONAL MATCH (t)-[:HAS_SCREENSHOT]->(s_tc:Screenshot)
        OPTIONAL MATCH (e)-[:CAPTURED_SCREENSHOT]->(s_exec:Screenshot)
        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s_def:Screenshot)
        OPTIONAL MATCH (e)-[:HAS_FAILURE_LOG]->(lc:LogChunk)
        WITH t,
             collect(DISTINCT properties(e))[..$limit] AS executions,
             collect(DISTINCT properties(d))[..$limit] AS defects,
             (collect(DISTINCT properties(s_tc)) + collect(DISTINCT properties(s_exec)) + collect(DISTINCT properties(s_def)))[..$limit] AS screenshots,
             collect(DISTINCT properties(lc))[..$limit] AS failure_logs
        RETURN properties(t) AS testcase,
               executions,
               defects,
               screenshots,
               failure_logs
        """
        with self._session() as session:
            result = session.run(cypher, {"id": test_case_id, "limit": limit})
            record = result.single()
            if record is None or record["testcase"] is None:
                return None
            executions = [_clean_props(e) for e in record["executions"] if e is not None]
            defects = [_clean_props(d) for d in record["defects"] if d is not None]
            screenshots = [_clean_props(s) for s in record["screenshots"] if s is not None]
            failure_logs = [_clean_props(l) for l in record.get("failure_logs", []) if l is not None]
            primary_execution = executions[0] if executions else None
            primary_defect = defects[0] if defects else None
            primary_failure_log = failure_logs[0] if failure_logs else None
            return {
                "testcase": _clean_props(record["testcase"]),
                "execution": primary_execution,
                "defect": primary_defect,
                "failure_log": primary_failure_log,
                "executions": executions,
                "defects": defects,
                "screenshots": screenshots,
                "failure_logs": failure_logs,
            }

    def get_ego_graph(
        self,
        entity_id: str,
        limit: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        2-hop ego-graph expansion for any detected entity.
        Returns the entity plus neighbors within 2 relationship steps with separate properties.
        """
        if not entity_id:
            return None
        if entity_id.startswith("TC-"):
            return self.get_testcase_context(entity_id, limit=limit)
        if entity_id.startswith("BUG-"):
            return self.get_full_defect_context(entity_id, limit=limit)
        if entity_id.startswith("EXEC-"):
            return self.get_execution_context(entity_id, limit=limit)
        if entity_id.startswith("SCR-"):
            return self.get_screenshot_context(entity_id)
        return None

    def get_screenshot_context(
        self,
        screenshot_id: str,
    ) -> Optional[Dict[str, Any]]:
        # Returns all three linked entity lists labelled by link type; never merges them
        cypher = """
        MATCH (s:Screenshot {screenshot_id: $id})
        OPTIONAL MATCH (t:TestCase)-[:HAS_SCREENSHOT]->(s)
        OPTIONAL MATCH (e:Execution)-[:CAPTURED_SCREENSHOT]->(s)
        OPTIONAL MATCH (d:Defect)-[:HAS_SCREENSHOT]->(s)
        RETURN properties(s) AS screenshot,
               collect(DISTINCT properties(t)) AS testcases,
               collect(DISTINCT properties(e)) AS executions,
               collect(DISTINCT properties(d)) AS defects
        """
        with self._session() as session:
            result = session.run(cypher, {"id": screenshot_id})
            record = result.single()
            if record is None or record["screenshot"] is None:
                return None
            return {
                "screenshot": _clean_props(record["screenshot"]),
                "testcases": [
                    _clean_props(t) for t in record["testcases"] if t is not None
                ],
                "executions": [
                    _clean_props(e) for e in record["executions"] if e is not None
                ],
                "defects": [
                    _clean_props(d) for d in record["defects"] if d is not None
                ],
            }

    def get_graph_context(self, entity_id: str) -> Any:
        return self.get_ego_graph(entity_id)

    # ---------------------------------------------------------
    # Vocabulary (Cached)
    # ---------------------------------------------------------

    def get_vocabulary(self) -> Dict[str, List[str]]:
        if self._vocabulary_cache is not None:
            return self._vocabulary_cache

        vocab = {
            "severity": [],
            "priority": [],
            "status": [],
            "bug_type": [],
            "execution_status": [],
            "environments": [],
            "modules": [],
        }

        with self._session() as session:
            # Defect vocabulary
            r = session.run(
                """
                MATCH (d:Defect)
                RETURN collect(DISTINCT d.severity) AS severities,
                       collect(DISTINCT d.priority) AS priorities,
                       collect(DISTINCT d.status) AS statuses,
                       collect(DISTINCT d.bug_type) AS bug_types
                """,
                {}
            ).single()
            if r:
                vocab["severity"] = sorted([str(x) for x in r["severities"] if x is not None])
                vocab["priority"] = sorted([str(x) for x in r["priorities"] if x is not None])
                vocab["status"] = sorted([str(x) for x in r["statuses"] if x is not None])
                vocab["bug_type"] = sorted([str(x) for x in r["bug_types"] if x is not None])

            # Execution status
            r_exec = session.run(
                "MATCH (e:Execution) RETURN collect(DISTINCT e.status) AS statuses",
                {}
            ).single()
            if r_exec:
                vocab["execution_status"] = sorted([str(x) for x in r_exec["statuses"] if x is not None])

            # Environments
            if self.has_environments:
                r_env = session.run("MATCH (env:Environment) RETURN collect(DISTINCT env.name) AS envs", {}).single()
                if r_env:
                    vocab["environments"] = sorted([str(x) for x in r_env["envs"] if x is not None])
            else:
                r_env = session.run("MATCH (e:Execution) RETURN collect(DISTINCT e.environment) AS envs", {}).single()
                if r_env:
                    vocab["environments"] = sorted([str(x) for x in r_env["envs"] if x is not None])

            # Modules
            if self.has_modules:
                r_mod = session.run("MATCH (m:Module) RETURN collect(DISTINCT m.name) AS mods", {}).single()
                if r_mod:
                    vocab["modules"] = sorted([str(x) for x in r_mod["mods"] if x is not None])
            else:
                r_mod = session.run("MATCH (d:Defect) RETURN collect(DISTINCT d.module) AS mods", {}).single()
                if r_mod:
                    vocab["modules"] = sorted([str(x) for x in r_mod["mods"] if x is not None])

        self._vocabulary_cache = vocab
        return vocab

    # ---------------------------------------------------------
    # Value Normalization Helper
    # ---------------------------------------------------------

    @staticmethod
    def normalize_filter_value(key: str, val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, (list, tuple, set)):
            return [Neo4jGraphRetriever.normalize_filter_value(key, item) for item in val if item is not None]

        val_str = str(val).strip()
        k_lower = key.lower()

        if k_lower == "regression":
            if val is True or val_str.lower() in ("yes", "true", "1", "y", "regression"):
                return "Yes"
            elif val is False or val_str.lower() in ("no", "false", "0", "n"):
                return "No"
            return val_str.capitalize()

        if k_lower == "environment":
            return val_str.upper()

        if k_lower == "severity":
            sev_map = {"blocker": "Blocker", "critical": "Critical", "major": "Major", "minor": "Minor"}
            return sev_map.get(val_str.lower(), val_str.capitalize())

        if k_lower == "priority":
            return val_str.upper()

        if k_lower == "status":
            status_map = {
                "closed": "Closed",
                "in progress": "In Progress",
                "inprogress": "In Progress",
                "resolved": "Resolved",
                "new": "New",
                "reopened": "Reopened",
            }
            return status_map.get(val_str.lower(), val_str.title())

        if k_lower == "reproducibility":
            rep_map = {
                "unable to reproduce": "Unable to Reproduce",
                "once": "Once",
                "intermittent": "Intermittent",
                "always": "Always",
            }
            return rep_map.get(val_str.lower(), val_str)

        if k_lower in ("found_in_build", "fixed_build"):
            if val_str.lower().startswith("b-") or val_str.lower().startswith("b"):
                return val_str.upper()

        if k_lower == "module":
            mod_map = {
                "hr": "HR", "crm": "CRM", "pos": "POS", "ecommerce": "eCommerce", "e-commerce": "eCommerce",
                "accounting": "Accounting", "documents": "Documents", "helpdesk": "Helpdesk",
                "inventory": "Inventory", "knowledge": "Knowledge", "maintenance": "Maintenance",
                "manufacturing": "Manufacturing", "payroll": "Payroll", "project": "Project",
                "purchase": "Purchase", "quality": "Quality", "rental": "Rental",
                "sales": "Sales", "studio": "Studio", "subscriptions": "Subscriptions", "website": "Website"
            }
            return mod_map.get(val_str.lower(), val_str)

        return val

    # ---------------------------------------------------------
    # Filter Templates
    # ---------------------------------------------------------

    DEFECT_FILTER_REGISTRY = {
        "severity": "d.severity",
        "priority": "d.priority",
        "status": "d.status",
        "bug_type": "d.bug_type",
        "type": "d.bug_type",
        "defect_type": "d.bug_type",
        "found_in_build": "d.found_in_build",
        "fixed_build": "d.fixed_build",
        "environment": "d.environment",
        "regression": "d.regression",
        "reproducibility": "d.reproducibility",
        "root_cause": "d.root_cause",
        "assigned_to": "d.assigned_to",
        "developer": "d.developer",
        "reported_by": "d.reported_by",
        "fix_version": "d.fix_version",
        "created_date": "d.created_date",
        "resolved_date": "d.resolved_date",
    }

    def defects_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        applied = {}
        unmapped = []
        where_clauses = []
        params = {"limit": limit}

        # Handle module filter (REPORTED_IN_MODULE if has_modules, else property)
        module_val = filters.get("module")
        if module_val:
            norm_mod = self.normalize_filter_value("module", module_val)
            if self.has_modules:
                match_clause = "MATCH (d:Defect)-[:REPORTED_IN_MODULE]->(m_filt:Module {name: $module_param})"
                params["module_param"] = norm_mod
                applied["module"] = norm_mod
            else:
                where_clauses.append("d.module = $module_param")
                params["module_param"] = norm_mod
                applied["module"] = norm_mod
        else:
            match_clause = "MATCH (d:Defect)"

        for k, v in filters.items():
            if v is None or v == "" or k == "module":
                continue
            orig_k = k
            if k in ("type", "defect_type"):
                if str(v).lower() in ("regression", "yes"):
                    k = "regression"
                    v = "Yes"
                else:
                    k = "bug_type"

            if k not in self.DEFECT_FILTER_REGISTRY:
                unmapped.append(orig_k)
                continue

            col = self.DEFECT_FILTER_REGISTRY[k]
            norm_v = self.normalize_filter_value(k, v)
            pname = f"p_{k}"
            if isinstance(norm_v, (list, tuple, set)):
                val_list = [x for x in norm_v if x is not None]
                if val_list:
                    where_clauses.append(f"{col} IN ${pname}")
                    params[pname] = val_list
                    applied[k] = val_list
            else:
                where_clauses.append(f"{col} = ${pname}")
                params[pname] = norm_v
                applied[k] = norm_v

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_cypher = f"""
        {match_clause}
        {where_str}
        RETURN count(d) AS total
        """

        # Sample query: optional hop for module after WITH d ORDER BY LIMIT
        module_select = "COALESCE(m.name, d.module) AS module" if self.has_modules else "d.module AS module"
        optional_mod = "OPTIONAL MATCH (d)-[:REPORTED_IN_MODULE]->(m:Module)" if self.has_modules else ""

        sample_cypher = f"""
        {match_clause}
        {where_str}
        WITH d ORDER BY d.defect_id
        LIMIT $limit
        {optional_mod}
        RETURN d.defect_id AS defect_id,
               d.title AS title,
               d.severity AS severity,
               d.priority AS priority,
               d.status AS status,
               d.bug_type AS bug_type,
               d.found_in_build AS found_in_build,
               {module_select}
        ORDER BY defect_id
        """

        with self._session() as session:
            total = session.run(count_cypher, params).single()["total"]
            sample_res = session.run(sample_cypher, params)
            sample = [dict(r) for r in sample_res]

        return {
            "template": "defects_by_filters",
            "total": total,
            "sample": sample,
            "limit": limit,
            "filters_applied": applied,
            "unmapped_filters": unmapped,
        }

    TC_FILTER_REGISTRY = {
        "priority": "t.priority",
        "severity": "t.severity",
        "status": "t.status",
        "feature": "t.feature",
        "automation_status": "t.automation_status",
    }

    def testcases_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        applied = {}
        where_clauses = []
        params = {"limit": limit}

        module_val = filters.get("module")
        has_module_filter = bool(module_val)

        match_clause = "MATCH (t:TestCase)"
        if has_module_filter and self.has_modules:
            match_clause = "MATCH (t:TestCase)-[:IN_MODULE]->(m_filt:Module {name: $module_param})"
            params["module_param"] = module_val
            applied["module"] = module_val
        elif has_module_filter:
            where_clauses.append("t.module = $module_param")
            params["module_param"] = module_val
            applied["module"] = module_val

        for k, col in self.TC_FILTER_REGISTRY.items():
            if k in filters and filters[k]:
                pname = f"p_{k}"
                where_clauses.append(f"{col} = ${pname}")
                params[pname] = filters[k]
                applied[k] = filters[k]

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_cypher = f"""
        {match_clause}
        {where_str}
        RETURN count(t) AS total
        """

        module_select = "COALESCE(m.name, t.module) AS module" if self.has_modules else "t.module AS module"
        optional_mod = "OPTIONAL MATCH (t)-[:IN_MODULE]->(m:Module)" if self.has_modules else ""

        sample_cypher = f"""
        {match_clause}
        {where_str}
        WITH t ORDER BY t.test_case_id
        LIMIT $limit
        {optional_mod}
        RETURN t.test_case_id AS test_case_id,
               {module_select},
               t.feature AS feature,
               t.priority AS priority,
               t.severity AS severity,
               t.status AS status
        ORDER BY test_case_id
        """

        with self._session() as session:
            total = session.run(count_cypher, params).single()["total"]
            sample_res = session.run(sample_cypher, params)
            sample = [dict(r) for r in sample_res]

        return {
            "template": "testcases_by_filters",
            "total": total,
            "sample": sample,
            "limit": limit,
            "filters_applied": applied,
        }

    EXEC_FILTER_REGISTRY = {
        "status": "e.status",
        "build": "e.build_number",
        "build_number": "e.build_number",
    }

    def executions_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        applied = {}
        where_clauses = []
        params = {"limit": limit}

        env_val = filters.get("environment")
        has_env_filter = bool(env_val)

        match_clause = "MATCH (e:Execution)"
        if has_env_filter and self.has_environments:
            match_clause = "MATCH (e:Execution)-[:RAN_IN]->(env_filt:Environment {name: $env_param})"
            params["env_param"] = env_val
            applied["environment"] = env_val
        elif has_env_filter:
            where_clauses.append("e.environment = $env_param")
            params["env_param"] = env_val
            applied["environment"] = env_val

        for k, col in self.EXEC_FILTER_REGISTRY.items():
            if k in filters and filters[k]:
                pname = f"p_{k}"
                where_clauses.append(f"{col} = ${pname}")
                params[pname] = filters[k]
                applied[k] = filters[k]

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_cypher = f"""
        {match_clause}
        {where_str}
        RETURN count(e) AS total
        """

        env_select = "COALESCE(env.name, e.environment) AS environment" if self.has_environments else "e.environment AS environment"
        optional_env = "OPTIONAL MATCH (e)-[:RAN_IN]->(env:Environment)" if self.has_environments else ""

        sample_cypher = f"""
        {match_clause}
        {where_str}
        WITH e ORDER BY e.execution_id
        LIMIT $limit
        {optional_env}
        RETURN e.execution_id AS execution_id,
               e.status AS status,
               e.build_number AS build,
               {env_select},
               e.test_case_id AS test_case_id
        ORDER BY execution_id
        """

        with self._session() as session:
            total = session.run(count_cypher, params).single()["total"]
            sample_res = session.run(sample_cypher, params)
            sample = [dict(r) for r in sample_res]

        return {
            "template": "executions_by_filters",
            "total": total,
            "sample": sample,
            "limit": limit,
            "filters_applied": applied,
        }

    # ---------------------------------------------------------
    # Aggregation Templates
    # ---------------------------------------------------------

    DEFECT_AGG_WHITELIST = {
        "module",
        "severity",
        "priority",
        "status",
        "bug_type",
        "environment",
        "root_cause",
        "reproducibility",
        "regression",
        "found_in_build",
        "fixed_build",
    }

    DEFECT_FILTER_FIELD_MAP = {
        "module": "m.name",
        "severity": "d.severity",
        "priority": "d.priority",
        "status": "d.status",
        "bug_type": "d.bug_type",
        "type": "d.bug_type",
        "defect_type": "d.bug_type",
        "environment": "d.environment",
        "root_cause": "d.root_cause",
        "reproducibility": "d.reproducibility",
        "regression": "d.regression",
        "found_in_build": "d.found_in_build",
        "fixed_build": "d.fixed_build",
        "assigned_to": "d.assigned_to",
        "developer": "d.developer",
        "reported_by": "d.reported_by",
        "fix_version": "d.fix_version",
        "created_date": "d.created_date",
        "resolved_date": "d.resolved_date",
    }

    def aggregate_defects(
        self,
        group_by: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Compute parametric aggregation of defects in Cypher over the full dataset.
        Supports WHERE filters (single scalar or list of allowed values).
        Whitelists group_by and filter fields against real schema names to prevent Cypher injection.
        """
        if group_by not in self.DEFECT_AGG_WHITELIST:
            raise ValueError(
                f"Field '{group_by}' is not in defect aggregation whitelist: {self.DEFECT_AGG_WHITELIST}"
            )

        limit_clamped = max(1, min(100, int(limit)))
        filters = filters or {}
        params: Dict[str, Any] = {"limit": limit_clamped}
        where_clauses: List[str] = []
        applied_filters: Dict[str, Any] = {}
        unmapped_filters: List[str] = []

        # Determine module join requirement
        needs_module_rel = (group_by == "module" or "module" in filters) and self.has_modules

        if needs_module_rel:
            match_clause = "MATCH (d:Defect)-[:REPORTED_IN_MODULE]->(m:Module)"
            group_key_expr = "m.name" if group_by == "module" else f"d.{group_by}"
        else:
            match_clause = "MATCH (d:Defect)"
            group_key_expr = "d.module" if group_by == "module" else f"d.{group_by}"

        where_clauses.append(f"{group_key_expr} IS NOT NULL")

        # Process WHERE filters
        for k, v in filters.items():
            if not v:
                continue
            orig_k = k
            if k in ("type", "defect_type"):
                if str(v).lower() in ("regression", "yes"):
                    k = "regression"
                    v = "Yes"
                else:
                    k = "bug_type"
            if k not in self.DEFECT_FILTER_FIELD_MAP:
                raise ValueError(
                    f"Filter field '{k}' is not allowed. Allowed filter fields: {set(self.DEFECT_FILTER_FIELD_MAP.keys())}"
                )

            param_name = f"filt_{k}"
            field_expr = "m.name" if (k == "module" and self.has_modules) else f"d.{k}"
            norm_v = self.normalize_filter_value(k, v)

            if isinstance(norm_v, (list, tuple, set)):
                val_list = [x for x in norm_v if x is not None]
                if val_list:
                    where_clauses.append(f"{field_expr} IN ${param_name}")
                    params[param_name] = val_list
                    applied_filters[k] = val_list
            else:
                where_clauses.append(f"{field_expr} = ${param_name}")
                params[param_name] = norm_v
                applied_filters[k] = norm_v

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cypher = f"""
        {match_clause}
        {where_str}
        RETURN {group_key_expr} AS key, count(d) AS count
        ORDER BY count DESC, key ASC
        LIMIT $limit
        """

        total_cypher = f"""
        {match_clause}
        {where_str}
        RETURN count(d) AS total
        """

        with self._session() as session:
            res = session.run(cypher, params)
            rows = [{"key": r["key"], "count": r["count"]} for r in res]
            total_res = session.run(total_cypher, params).single()
            total = total_res["total"] if total_res else sum(r["count"] for r in rows)

        return {
            "template": f"aggregate_defects_by_{group_by}",
            "rows": rows,
            "total": total,
            "group_by": group_by,
            "filters_applied": applied_filters,
            "unmapped_filters": unmapped_filters,
        }

    def count_defects_by(self, field: str, limit: int = 50) -> Dict[str, Any]:
        return self.aggregate_defects(group_by=field, filters=None, limit=limit)

    EXEC_AGG_WHITELIST = {"status", "build", "environment"}

    def count_executions_by(self, field: str) -> Dict[str, Any]:
        if field not in self.EXEC_AGG_WHITELIST:
            raise ValueError(f"Field '{field}' is not in execution aggregation whitelist: {self.EXEC_AGG_WHITELIST}")

        limit_clause = "LIMIT 50" if field == "build" else ""

        if field == "environment" and self.has_environments:
            cypher = f"""
            MATCH (e:Execution)-[:RAN_IN]->(env:Environment)
            RETURN env.name AS key, count(e) AS count
            ORDER BY count DESC, key ASC
            {limit_clause}
            """
        else:
            field_prop = "build_number" if field == "build" else field
            cypher = f"""
            MATCH (e:Execution)
            WHERE e.{field_prop} IS NOT NULL
            RETURN e.{field_prop} AS key, count(e) AS count
            ORDER BY count DESC, key ASC
            {limit_clause}
            """

        with self._session() as session:
            res = session.run(cypher, {})
            rows = [{"key": r["key"], "count": r["count"]} for r in res]
            total = sum(r["count"] for r in rows)

        return {
            "template": f"count_executions_by_{field}",
            "rows": rows,
            "total": total,
        }

    def count_testcases_by_module(self) -> Dict[str, Any]:
        if self.has_modules:
            cypher = """
            MATCH (t:TestCase)-[:IN_MODULE]->(m:Module)
            RETURN m.name AS key, count(t) AS count
            ORDER BY count DESC, key ASC
            """
        else:
            cypher = """
            MATCH (t:TestCase)
            WHERE t.module IS NOT NULL
            RETURN t.module AS key, count(t) AS count
            ORDER BY count DESC, key ASC
            """

        with self._session() as session:
            res = session.run(cypher, {})
            rows = [{"key": r["key"], "count": r["count"]} for r in res]
            total = sum(r["count"] for r in rows)

        return {
            "template": "count_testcases_by_module",
            "rows": rows,
            "total": total,
        }

    def top_modules_by_defects(self, k: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.aggregate_defects(group_by="module", filters=filters, limit=k)


# =============================================================
# TEST DEMO
# =============================================================

if __name__ == "__main__":
    retriever = Neo4jGraphRetriever()
    try:
        print("=" * 60)
        print("NEO4J GRAPH RETRIEVER DEMO")
        print("=" * 60)

        ok = retriever.test_connection()
        print(f"Connected to {retriever.database}: {ok}")

        vocab = retriever.get_vocabulary()
        print(f"Vocabulary severities: {vocab['severity']}")
        print(f"Vocabulary environments: {vocab['environments']}")
        print(f"Vocabulary modules count: {len(vocab['modules'])}")

        crit = retriever.defects_by_filters({"severity": "Critical"}, limit=5)
        print(f"Critical defects total: {crit['total']}, sample rows: {len(crit['sample'])}")

        sev_agg = retriever.count_defects_by("severity")
        print(f"Defects by severity total: {sev_agg['total']}, groups: {len(sev_agg['rows'])}")

        top_mod = retriever.top_modules_by_defects(5)
        print(f"Top 5 modules by defects total: {top_mod['total']}, rows: {len(top_mod['rows'])}")
        print("=" * 60)
    finally:
        retriever.close()