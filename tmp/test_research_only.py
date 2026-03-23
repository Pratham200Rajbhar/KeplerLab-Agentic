"""Deep /research test — runs in background, logs to file."""
import asyncio, os, sys, time
sys.path.insert(0, "/disk1/KeplerLab_Agentic/backend")
os.chdir("/disk1/KeplerLab_Agentic/backend")

OUT = "/disk1/KeplerLab_Agentic/tmp/test_results"
os.makedirs(OUT, exist_ok=True)

async def run_research(query, label):
    from app.services.tools.research_tool import execute
    from app.services.chat_v2.schemas import ToolResult
    print(f"[RESEARCH] {label}\n  {query}", flush=True)
    t0 = time.time()
    events, result = [], None
    try:
        async for item in execute(query=query, user_id="test", notebook_id="nb1", session_id="s1"):
            if isinstance(item, ToolResult):
                result = item
            else:
                events.append(item)
                # Live progress
                if "research_phase" in item or "research_source" in item:
                    print(f"  {item[:120].strip()}", flush=True)
        
        elapsed = time.time() - t0
        if result and result.success:
            sc = result.metadata.get("sources_count", 0)
            content = result.content or ""
            report = (
                f"QUERY: {query}\nELAPSED: {elapsed:.1f}s\nSOURCES: {sc}\n\n"
                f"--- SSE EVENTS ---\n" + "\n".join(events[:60]) +
                f"\n\n--- REPORT (first 10000 chars) ---\n{content[:10000]}"
            )
            path = f"{OUT}/research_{label}.txt"
            open(path, "w").write(report)
            print(f"\n  ✓ {sc} sources, {elapsed:.1f}s → {path}", flush=True)
        else:
            err = result.content if result else "No result"
            print(f"\n  ✗ FAILED: {err[:300]}", flush=True)
            open(f"{OUT}/research_{label}_fail.txt", "w").write("\n".join(events) + "\n" + str(err))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\n  ✗ EXCEPTION: {e}", flush=True)
        open(f"{OUT}/research_{label}_error.txt", "w").write(tb)

asyncio.run(run_research("impact of large language models on software development", "llm_impact"))
