"""
Live End-to-End Pipeline & Video Generation Integration Test
Executes a full video generation job and verifies that both .html and .mp4 outputs are produced.
"""

import asyncio
import os
import sys

# Ensure repository root is in python path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from dotenv import load_dotenv
load_dotenv()

from backend.app.pipeline.orchestrator import process_video_job

async def run_live_test():
    prompt = "Explain Docker containers for beginners in 3 simple steps"
    test_job_id = "00000000-0000-0000-0000-000000000001"
    print("=" * 80)
    print(f"[START] STARTING END-TO-END PIPELINE LIVE TEST FOR PROMPT: '{prompt}'")
    print("=" * 80)

    try:
        res = await process_video_job(prompt=prompt, job_id=test_job_id)
        
        print("\n" + "=" * 80)
        print("[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"Job ID: {res.get('job_id')}")
        print(f"Status: {res.get('status')}")
        print(f"Video URL: {res.get('video_url')}")
        print("=" * 80)

        job_id = res.get("job_id")
        renders_dir = os.path.join(repo_root, "data", "renders")
        html_file = os.path.join(renders_dir, f"{job_id}.html")
        mp4_file = os.path.join(renders_dir, f"{job_id}.mp4")

        print("\n[VERIFYING FILE OUTPUTS ON DISK]")
        
        # Check HTML file
        if os.path.exists(html_file):
            size_kb = os.path.getsize(html_file) / 1024.0
            print(f"  [OK] HTML File Present: {html_file} ({size_kb:.2f} KB)")
        else:
            print(f"  [FAIL] HTML File MISSING: {html_file}")

        # Check MP4 file
        if os.path.exists(mp4_file):
            size_mb = os.path.getsize(mp4_file) / (1024.0 * 1024.0)
            print(f"  [OK] MP4 Video File Present: {mp4_file} ({size_mb:.2f} MB)")
            if size_mb > 0:
                print("  [SUCCESS] MP4 VIDEO SUCCESSFULLY GENERATED AND READY FOR DOWNLOAD!")
            else:
                print("  [WARNING] MP4 file is 0 bytes")
        else:
            print(f"  [FAIL] MP4 Video File MISSING: {mp4_file}")

        print("=" * 80)

    except Exception as err:
        print(f"\n[ERROR] PIPELINE LIVE TEST FAILED WITH ERROR: {err}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_live_test())
