import os
import sys
import json

# Setup environment
os.environ["PATH"] = r"C:\Users\ANB\AppData\Roaming\Python\Python314\Scripts;" + os.environ.get("PATH", "")
os.environ["SUITEST_API_URL"] = "http://127.0.0.1:4000"
os.environ["SUITEST_API_KEY"] = "sk_suitest_4ZBlLPcFaGdmoihBKOWA3R3ecEkBH6DJ7pI4WeCf54w"
os.environ["SUITEST_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
os.environ["SUITEST_TEST_USERNAME"] = "dev@suitest.local"
os.environ["SUITEST_TEST_PASSWORD"] = "AdminPassword123!"
os.environ["SUITEST_EVIDENCE_RECORDING"] = "false"
os.environ["PYTHONPATH"] = r"C:\Users\ANB\.gemini\antigravity\scratch\suitest\packages\lifecycle\src"

sys.path.insert(0, r"C:\Users\ANB\.gemini\antigravity\scratch\suitest\packages\lifecycle\src")

from suitest_lifecycle.blackbox.mcp import (
    blackbox_discover_app,
    blackbox_generate_playwright_tests,
    blackbox_run_playwright_tests,
    blackbox_collect_evidence,
    blackbox_publish_results,
    blackbox_summarize_findings
)

def main():
    print("=========================================================================", flush=True)
    print("Starting Direct Suitest MCP Blackbox Pipeline for Local Demo App...", flush=True)
    print("=========================================================================\n", flush=True)

    target_url = "http://127.0.0.1:3000"
    username = "dev@suitest.local"
    password = "AdminPassword123!"
    project_id = "r37knkk7s7xlebxpchho20ht"

    # Step 1: Discover App
    print("STEP 1: Discovering Application at http://127.0.0.1:3000...", flush=True)
    disc = blackbox_discover_app(url=target_url, username=username, password=password, max_routes=5)
    print(f"Discovery Summary: {disc.get('summary')}", flush=True)
    print(f"Discovery Success: {disc.get('success')}\n", flush=True)

    # Step 2: Generate Playwright Tests
    print("STEP 2: Generating Playwright Tests...", flush=True)
    gen = blackbox_generate_playwright_tests(url=target_url)
    print(f"Generation Summary: {gen.get('summary')}", flush=True)
    print(f"Generated Files: {gen.get('artifacts')}\n", flush=True)

    # Step 3: Run Playwright Tests
    print("STEP 3: Running Playwright Tests...", flush=True)
    run = blackbox_run_playwright_tests(url=target_url)
    print(f"Run Summary: {run.get('summary')}", flush=True)
    print(f"Run Success: {run.get('success')}\n", flush=True)

    # Step 4: Collect Evidence
    print("STEP 4: Indexing Evidence...", flush=True)
    ev = blackbox_collect_evidence(url=target_url)
    print(f"Evidence Summary: {ev.get('summary')}\n", flush=True)

    # Step 5: Publish Results
    print("STEP 5: Publishing Results to Suitest Web Dashboard...", flush=True)
    pub = blackbox_publish_results(url=target_url, project_id=project_id)
    print(f"Publish Summary: {pub.get('summary')}", flush=True)
    print(f"Publish Success: {pub.get('success')}\n", flush=True)

    # Step 6: Summarize Findings
    print("STEP 6: Generating Final Summary Findings...", flush=True)
    summary = blackbox_summarize_findings(url=target_url)
    print("=========================================================================", flush=True)
    print("FINAL SUMMARY FINDINGS:", flush=True)
    print("=========================================================================", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

if __name__ == "__main__":
    main()
