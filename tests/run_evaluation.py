import asyncio
import json
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import Orchestrator
from tests.test_baseline import SingleAgentBaseline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("evaluator")

PROMPTS_FILE = Path(__file__).resolve().parent / "eval_prompts.json"
RESULTS_DIR = Path(__file__).resolve().parent / "eval_results"


async def run_evaluation():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    baseline = SingleAgentBaseline()
    orchestrator = Orchestrator()

    # Pre-index knowledge base once
    await orchestrator.ensure_indexed()

    summary_rows = []

    for item in prompts:
        prompt_id = item["id"]
        prompt_text = item["prompt"]
        traps = item.get("traps", [])
        advantage = item.get("expected_triad_advantage", "")

        logger.info("=== Running Eval Prompt [%s] ===", prompt_id)
        print(f"\n{'='*60}\nEvaluating: {prompt_id}\n{'='*60}")

        baseline_file = RESULTS_DIR / f"{prompt_id}_baseline.md"
        triad_file = RESULTS_DIR / f"{prompt_id}_triad.md"
        if baseline_file.exists() and triad_file.exists() and "--force" not in sys.argv:
            logger.info("[%s] Both baseline and triad results already exist. Skipping.", prompt_id)
            continue

        # 1. Run Baseline
        logger.info("[%s] Running single-agent baseline...", prompt_id)
        t0 = time.perf_counter()
        baseline_output = await baseline.run(prompt_text)
        baseline_time = time.perf_counter() - t0
        logger.info("[%s] Baseline complete in %.1fs", prompt_id, baseline_time)

        # Baseline file
        baseline_file = RESULTS_DIR / f"{prompt_id}_baseline.md"
        with open(baseline_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Evaluation Prompt: {prompt_id} (Single-Agent Baseline)\n\n"
                f"**Prompt:**\n> {prompt_text}\n\n"
                f"**Known Traps:**\n"
                + "\n".join(f"- {t}" for t in traps)
                + f"\n\n**Latency:** {baseline_time:.2f}s\n\n"
                f"---\n\n## Generated Output\n\n{baseline_output}\n"
            )

        # Sleep briefly to avoid Groq burst rate limits
        await asyncio.sleep(2.0)

        # 2. Run Triad
        logger.info("[%s] Running AKILI-SPECS triad...", prompt_id)
        t1 = time.perf_counter()
        triad_output = await orchestrator.run(prompt_text)
        triad_time = time.perf_counter() - t1
        logger.info("[%s] Triad complete in %.1fs", prompt_id, triad_time)

        # Extract audit references from execution log
        rag_refs = []
        for log_entry in orchestrator.execution_log:
            if log_entry.get("stage") == "audit":
                rag_refs.extend(log_entry.get("references", []))
        unique_refs = list(dict.fromkeys(rag_refs))

        # Extract aggregate report from execution log
        agg_report = {}
        for log_entry in orchestrator.execution_log:
            if log_entry.get("stage") == "aggregate":
                agg_report = log_entry.get("report", {})

        # Triad file
        triad_file = RESULTS_DIR / f"{prompt_id}_triad.md"
        with open(triad_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Evaluation Prompt: {prompt_id} (AKILI-SPECS Triad)\n\n"
                f"**Prompt:**\n> {prompt_text}\n\n"
                f"**Known Traps:**\n"
                + "\n".join(f"- {t}" for t in traps)
                + f"\n\n**Expected Triad Advantage:**\n{advantage}\n\n"
                f"**Latency:** {triad_time:.2f}s\n\n"
                f"**Tasks Decomposed:** {agg_report.get('total_tasks', 1)}\n"
                f"**Passed Directly:** {agg_report.get('passed', 1)}\n"
                f"**Retried & Passed:** {agg_report.get('failed_then_passed', 0)}\n"
                f"**Force Merged:** {agg_report.get('force_merged', 0)}\n"
                f"**Issues Resolved:** {agg_report.get('issues_resolved', 0)} / {agg_report.get('total_issues_found', 0)}\n\n"
                f"**Grounding References Cited:**\n"
                + "\n".join(f"- {r}" for r in unique_refs)
                + f"\n\n---\n\n## Generated Output\n\n{triad_output}\n"
            )

        summary_rows.append({
            "id": prompt_id,
            "baseline_time": round(baseline_time, 1),
            "triad_time": round(triad_time, 1),
            "tasks": agg_report.get("total_tasks", 1),
            "retries": agg_report.get("failed_then_passed", 0),
            "force_merges": agg_report.get("force_merged", 0),
            "citations": len(unique_refs),
        })

        await asyncio.sleep(2.0)

    # Print summary table
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY: BASELINE vs AKILI-SPECS TRIAD")
    print("=" * 80)
    print(f"{'Prompt ID':<15} | {'Base (s)':<9} | {'Triad (s)':<10} | {'Tasks':<6} | {'Retried':<8} | {'Merged':<7} | {'Citations':<10}")
    print("-" * 80)
    for row in summary_rows:
        print(
            f"{row['id']:<15} | {row['baseline_time']:<9} | {row['triad_time']:<10} | "
            f"{row['tasks']:<6} | {row['retries']:<8} | {row['force_merges']:<7} | {row['citations']:<10}"
        )
    print("=" * 80)
    print(f"Results saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
