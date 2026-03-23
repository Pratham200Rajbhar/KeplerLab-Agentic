"""
Direct integration test for /web and /research tools.
Runs in-process, no auth needed.
Saves results to /disk1/KeplerLab_Agentic/tmp/test_results/
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, "/disk1/KeplerLab_Agentic/backend")
os.chdir("/disk1/KeplerLab_Agentic/backend")

OUT_DIR = "/disk1/KeplerLab_Agentic/tmp/test_results"
os.makedirs(OUT_DIR, exist_ok=True)


def save(filename: str, content: str):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  → Saved: {path}")


async def collect_tool_output(gen) -> dict:
    """Consume an async generator from a tool, collecting SSE events and ToolResult."""
    events = []
    tool_result = None
    from app.services.chat_v2.schemas import ToolResult
    async for item in gen:
        if isinstance(item, ToolResult):
            tool_result = item
        elif isinstance(item, str):
            events.append(item)
    return {"events": events, "result": tool_result}


def format_report(label: str, query: str, data: dict, elapsed: float) -> str:
    lines = [
        f"=" * 70,
        f"TEST: {label}",
        f"Query: {query}",
        f"Elapsed: {elapsed:.1f}s",
        f"=" * 70,
        "",
        "── SSE EVENTS ──",
    ]
    for e in data["events"]:
        lines.append(e.strip())

    lines += ["", "── TOOL RESULT ──"]
    r = data["result"]
    if r:
        lines.append(f"success: {r.success}")
        lines.append(f"metadata: {r.metadata}")
        lines.append("")
        lines.append("── CONTENT (first 6000 chars) ──")
        lines.append((r.content or "")[:6000])
    else:
        lines.append("NO ToolResult received!")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# WEB TESTS
# ──────────────────────────────────────────────────────────────────────────────

async def test_web(query: str, label: str) -> bool:
    print(f"\n[WEB] {label}")
    print(f"  Query: {query}")
    from app.services.tools.web_search_tool import execute
    t0 = time.time()
    try:
        data = await collect_tool_output(execute(query=query, user_id="test"))
        elapsed = time.time() - t0
        report = format_report(f"WEB: {label}", query, data, elapsed)
        save(f"web_{label.lower().replace(' ', '_')}.txt", report)

        r = data["result"]
        if not r or not r.success:
            print(f"  ✗ FAILED — no successful result")
            return False

        sources = r.metadata.get("sources", [])
        queries = r.metadata.get("queries", [])
        print(f"  ✓ OK — {len(sources)} sources, {len(queries)} queries, {elapsed:.1f}s")
        print(f"    Content preview: {(r.content or '')[:200]!r}")
        return True
    except Exception as exc:
        elapsed = time.time() - t0
        print(f"  ✗ EXCEPTION after {elapsed:.1f}s: {exc}")
        import traceback
        save(f"web_{label.lower().replace(' ', '_')}_error.txt", traceback.format_exc())
        return False


# ──────────────────────────────────────────────────────────────────────────────
# RESEARCH TESTS
# ──────────────────────────────────────────────────────────────────────────────

async def test_research(query: str, label: str) -> bool:
    print(f"\n[RESEARCH] {label}")
    print(f"  Query: {query}")
    from app.services.tools.research_tool import execute
    t0 = time.time()
    try:
        data = await collect_tool_output(execute(
            query=query,
            user_id="test",
            notebook_id="test-notebook",
            session_id="test-session",
        ))
        elapsed = time.time() - t0
        report = format_report(f"RESEARCH: {label}", query, data, elapsed)
        save(f"research_{label.lower().replace(' ', '_')}.txt", report)

        r = data["result"]
        if not r or not r.success:
            print(f"  ✗ FAILED — no successful result")
            return False

        sources_count = r.metadata.get("sources_count", 0)
        print(f"  ✓ OK — {sources_count} sources cited, {elapsed:.1f}s")
        print(f"    Content preview: {(r.content or '')[:200]!r}")
        return True
    except Exception as exc:
        elapsed = time.time() - t0
        print(f"  ✗ EXCEPTION after {elapsed:.1f}s: {exc}")
        import traceback
        save(f"research_{label.lower().replace(' ', '_')}_error.txt", traceback.format_exc())
        return False


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("KeplerLab /web and /research Integration Tests")
    print("=" * 70)

    results = {}

    # WEB tests — varied complexity
    web_cases = [
        ("latest AI news 2025", "simple_news"),
        ("how does CRISPR gene editing work", "science_explanation"),
        ("Python vs JavaScript for backend development in 2025", "tech_comparison"),
    ]

    for query, label in web_cases:
        ok = await test_web(query, label)
        results[f"web_{label}"] = ok
        # Small delay to be polite to DDG
        await asyncio.sleep(2)

    # RESEARCH test — only one deep test (takes time)
    research_cases = [
        ("impact of large language models on software development", "llm_impact"),
    ]

    for query, label in research_cases:
        ok = await test_research(query, label)
        results[f"research_{label}"] = ok

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for k, v in results.items():
        status = "✓ PASS" if v else "✗ FAIL"
        print(f"  {status}  {k}")
    print(f"\n{passed}/{total} tests passed")
    print(f"Results saved to: {OUT_DIR}/")

    return all(results.values())


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
