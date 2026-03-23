"""Quick /web only tests — runs in ~2 min."""
import asyncio, os, sys, time
sys.path.insert(0, "/disk1/KeplerLab_Agentic/backend")
os.chdir("/disk1/KeplerLab_Agentic/backend")

OUT = "/disk1/KeplerLab_Agentic/tmp/test_results"
os.makedirs(OUT, exist_ok=True)

async def collect(gen):
    from app.services.chat_v2.schemas import ToolResult
    events, result = [], None
    async for item in gen:
        if isinstance(item, ToolResult):
            result = item
        else:
            events.append(item)
    return events, result

async def run_web(query, label):
    from app.services.tools.web_search_tool import execute
    print(f"\n[WEB] {label}\n  {query}")
    t0 = time.time()
    try:
        events, r = await collect(execute(query=query, user_id="test"))
        elapsed = time.time() - t0
        if r and r.success:
            sources = r.metadata.get("sources", [])
            queries = r.metadata.get("queries", [])
            content = r.content or ""
            report = (
                f"QUERY: {query}\nELAPSED: {elapsed:.1f}s\nSOURCES: {len(sources)}\n"
                f"QUERIES USED: {queries}\n\n"
                + "\n".join(f"  [{i+1}] {s['title']} — {s['url']}" for i, s in enumerate(sources))
                + "\n\n--- SYNTHESIZED CONTEXT (first 8000 chars) ---\n"
                + content[:8000]
            )
            path = f"{OUT}/web_{label}.txt"
            open(path, "w").write(report)
            print(f"  ✓ {len(sources)} sources, {len(queries)} queries, {elapsed:.1f}s → {path}")
            return True
        else:
            err = (r.content if r else "No result")
            print(f"  ✗ FAILED: {err[:200]}")
            open(f"{OUT}/web_{label}_fail.txt", "w").write("\n".join(events) + "\n" + str(err))
            return False
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"  ✗ EXCEPTION: {e}")
        open(f"{OUT}/web_{label}_error.txt", "w").write(tb)
        return False

async def main():
    cases = [
        ("latest AI news 2025", "simple_news"),
        ("how does CRISPR gene editing work", "science_explanation"),
        ("Python vs JavaScript backend 2025", "tech_comparison"),
        ("what is quantum computing current state", "complex_query"),
    ]
    results = {}
    for query, label in cases:
        results[label] = await run_web(query, label)
        await asyncio.sleep(1)
    
    print("\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"  {'✓' if v else '✗'} web_{k}")
    passed = sum(results.values())
    print(f"\n{passed}/{len(results)} passed")

asyncio.run(main())
