import sys
import json
import asyncio
import argparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler
from graph.final_prompt import GroundedPromptBuilder


async def execute_query(query_text: str, show_full_json: bool = False):
    print("=" * 80)
    print(f"GRAPHRAG QUERY: {query_text}")
    print("=" * 80)

    retriever = HybridRetriever()
    assembler = ContextAssembler()
    prompt_builder = GroundedPromptBuilder()

    try:
        await retriever.initialize()

        # Step 1: Retrieval
        retrieval_res = await retriever.retrieve(query_text)
        trace = retrieval_res.get("trace", {})
        route = retrieval_res.get("route", {})
        plan = route.get("plan", {})

        # Step 2: Context Assembly
        context = assembler.assemble(retrieval_res)

        print("\n" + "=" * 80)
        print("RETRIEVAL SUMMARY")
        print("=" * 80)
        print(f"• Query:         {query_text}")
        print(f"• Intent:        {trace.get('intent')}")
        print(f"• Target Entity: {plan.get('target_entity')}")
        print(f"• Operation:     {plan.get('operation')}")
        print(f"• Route:         {route.get('route')}")
        print(f"• Plan Kind:     {plan.get('kind')}")
        print(f"• Backend:       {trace.get('backend')}")
        print(f"• Latency:       {trace.get('latency_ms')} ms")
        print(f"• Total Rows:    {trace.get('row_count')}")

        notes = context.get("notes", {})
        if notes.get("not_found_ids"):
            print(f"• NOT FOUND IDs: {notes['not_found_ids']}")
        if notes.get("links_missing"):
            print(f"• Missing Links: True (execution or defect links missing)")
        if notes.get("unmapped_filters"):
            print(f"• Unmapped Filters: {notes['unmapped_filters']}")
        if notes.get("fallback_used"):
            print(f"• Fallback Triggered: {notes['fallback_used']}")

        # Display evidence preview
        entities = context.get("entities", [])
        relationships = context.get("relationships", [])
        ranked_hits = context.get("ranked_hits", [])
        filter_res = context.get("filter_results")
        aggregates = context.get("aggregates")

        print("\n" + "-" * 80)
        print("EVIDENCE DETAILS")
        print("-" * 80)

        if filter_res:
            print(f"• Filter Total:  {filter_res.get('total')}")
            sample = filter_res.get("sample", [])
            print(f"• Sample Size:   {len(sample)} rows displayed")
            for item in sample[:5]:
                print(f"    - {item}")
            if len(sample) > 5:
                print(f"    ... and {len(sample) - 5} more sample items.")

        elif aggregates:
            print(f"• Aggregation Template: {aggregates.get('template')}")
            print(f"• Total Sum:            {aggregates.get('total')}")
            for row in aggregates.get("rows", []):
                print(f"    - {row.get('key')}: {row.get('count')}")

        elif ranked_hits:
            print(f"• Top {len(ranked_hits)} Semantic Hits:")
            for rank, hit in enumerate(ranked_hits[:5], 1):
                score_str = f"score={hit.get('fused_score', hit.get('score', 0)):.4f}"
                title = hit.get('title') or hit.get('screen_name') or hit.get('feature') or ""
                item_id = hit.get('defect_id') or hit.get('screenshot_id') or hit.get('test_case_id')
                print(f"    {rank}. [{item_id}] {title} ({score_str})")
            if len(ranked_hits) > 5:
                print(f"    ... and {len(ranked_hits) - 5} more hits.")

        elif entities:
            print(f"• Structured Entities ({len(entities)}):")
            for ent in entities[:5]:
                print(f"    - [{ent.get('type')}] {ent.get('id')}")
            if relationships:
                print(f"• Structured Relationships ({len(relationships)}):")
                for rel in relationships[:5]:
                    print(f"    - ({rel.get('source_id')}) -[:{rel.get('relationship')}]-> ({rel.get('target_id')})")

        if show_full_json:
            print("\n" + "=" * 80)
            print("FULL ASSEMBLED CONTEXT (JSON)")
            print("=" * 80)
            print(json.dumps(context, indent=2, ensure_ascii=False, default=str))

    finally:
        retriever.close()


def main():
    parser = argparse.ArgumentParser(description="Run a query through the GraphRAG retrieval pipeline")
    parser.add_argument("query", nargs="?", type=str, help="Question or query string (e.g. 'BUG-000176 details')")
    parser.add_argument("--json", action="store_true", help="Print full assembled context JSON")
    args = parser.parse_args()

    query_str = args.query
    if not query_str:
        try:
            query_str = input("Enter query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    if not query_str:
        print("No query provided. Example usage:")
        print("  python query.py \"BUG-000176 details\"")
        print("  python query.py \"show all Critical defects\"")
        print("  python query.py \"defects about login timeouts\"")
        sys.exit(1)

    asyncio.run(execute_query(query_str, show_full_json=args.json))


if __name__ == "__main__":
    main()
