# 📑 Project Integration Blueprint: Asset Service Module
**Module:** `asset_service`  
**Engineer:** Omar Eldaly (Asset Service)  
**Integration Target:** `main`  

This documentation details the foundational code implemented for Stage 5 (Asset Service). It explains the purpose behind every component and explicitly highlights how each member of our cohort connects to this structure, along with clear steps for following up or modifying my work.

---

## 📂 Core Architecture: What I Have Done

### 1. `asset_service/asset.py` (The Data Validation Layer)
*   **What it is:** The structural contract defining incoming payloads (`AssetRequest`) and outgoing server responses (`AssetResponse`) using Pydantic models.
*   **What it does:** It acts as a gatekeeper, validating that incoming strings, field lengths, and required metadata are structured flawlessly. If the incoming data is corrupted, Pydantic halts it immediately before it hits our internal systems.
*   **Why it’s built this way:** The fields support mutable states. This enables a flexible **Human-in-the-Loop** style where intermediate adjustments can be made to asset properties without failing background data integrity checks.

### 2. `asset_service/images.py` (The Async Engine)
*   **What it is:** The execution shell housing our core generator routines (`AssetService` and `generate_asset_mock`).
*   **What it does:** Built on native Python `async/await` syntax. It processes the long-running aspects of asset creation (network latency, model computation) without freezing our main application loop.
*   **Why it’s built this way:** Generating images or heavy data files can take seconds. Asynchronous handlers ensure our application server remains unblocked and responsive to other active users while a generation occurs.

### 3. `asset_service/__init__.py` (The Public API Boundary)
*   **What it is:** The package encapsulation layout exposing a clean top-level export array (`__all__`).
*   **What it does:** It completely hides internal file locations. Teammates can easily tap into our service using a clean import path: `from asset_service import AssetService`.

### 4. `test_assets.py` (The Automated QA Framework)
*   **What it is:** A local validation test runner built using the `pytest` engine.
*   **What it does:** Simulates request vectors to confirm contract serialization and async handling behave deterministically. **Currently executing at a 100% local pass rate.**

---

## 👥 Cross-Lane Connections: Team Action Items

### 🏗️ 1. Pipeline Orchestrator — Omar Dorgham
*   **How Our Tasks Connect:** You are building the main FastAPI app and managing the asynchronous pipeline loop. My `AssetService` relies on `async def` functions so that it interfaces seamlessly with your Orchestrator without blocking the event loop.
*   **How to Follow Up or Modify My Code:** Import my module directly into your main FastAPI router file. When the pipeline reaches Stage 5, invoke the service using an asynchronous `await` call:
    ```python
    from asset_service import AssetService

    # Inside your main orchestrator loop
    asset_service = AssetService()
    asset_data = await asset_service.generate_asset_mock(mostafa_bahy_scene_output)
    ```

### 🎨 2. Stage 6: Composition — Nada Ahmed Samir
*   **How Our Tasks Connect:** Your stage takes the assets, layouts, and timestamps to build the final blueprint for the video renderer. My module outputs a clean asset map containing royalty-free image/SVG links stored in Supabase.
*   **How to Follow Up or Modify My Code:** In your composition module, look at the output structure of `AssetResponse`. You will read my URLs and pair them up with Osama's timestamps:
    ```python
    # Use my asset mapping output to compose your timeline array
    asset_url = asset_response.output_url
    # Merge asset_url with corresponding timestamp and visual elements
    ```

### 🤖 3. Stage 2: Scene Planner — Mostafa Bahy
*   **How Our Tasks Connect:** My stage consumes your layout plans and visual cues. The text descriptions you output under your `visual_elements` contract are used by my service to fetch or generate matching royalty-free images.
*   **How to Follow Up or Modify My Code:** If you modify your scene output structure or alter the schema names for `visual_elements`, update the input parsing fields inside `asset_service/asset.py` to keep the JSON contract aligned.

### 🗄️ 4. Cloud Infrastructure, Storage & Database — Team (Supabase Integration)
*   **How Our Tasks Connect:** The goal of the asset service is to store fetched or generated assets directly into a Supabase Storage bucket. Right now, it produces simulated repository paths.
*   **How to Follow Up or Modify My Code:** Open `asset_service/images.py` and replace the mock URL return statement with your live Supabase client bucket upload routine:
    ```python
    from supabase import create_client

    # Initialize your client session
    supabase = create_client(URL, KEY)
    
    # Upload downloaded media assets into your bucket
    await supabase.storage.from_("asset-library").upload(
        path=f"scenes/{request.title}.png", 
        file=fetched_binary
    )
    ```

### 🖼️ 5. Stage 7: Animation & Render — Youssef Mohamed
*   **How Our Tasks Connect:** You are stitching the audio and the visual map compiled by Nada into a final MP4 via FFmpeg. My service handles downloading and resolving the raw visual assets into locally accessible assets or remote image URLs so your rendering routines run cleanly.
*   **How to Follow Up or Modify My Code:** If your FFmpeg pipeline struggles with specific image aspect ratios, you can communicate those restrictions to me, and we can add constraint checks directly inside the `AssetRequest` schema validation layer.

### ✍️ 6. Stage 1: Intake & Transcript — Ahmed Eid
*   **How Our Tasks Connect:** You write the initial structured script that includes the baseline text and initial visual cues. My schemas are designed with mutable fields to fully support "Human-in-the-Loop" edits if a user updates your script right before the video begins rendering.

### 🎙️ 7. Stage 3 & Stage 4: Voiceover & Alignment — Mohamed Mahdy & Osama Bayomi
*   **How Our Tasks Connect:** You are generating the narration tracks and word-level timestamps using Gemini and Whisper. The assets my service retrieves will be systematically timed to your generated timestamps during Nada’s composition stage. No code modifications are needed on your end to interact with my module.

---

## 🚀 Running and Verifying the Module
To pull down my branch and confirm that new modifications or connection layers pass our data layer validation suites, execute these statements locally:

```bash
# 1. Guarantee package matching states
pip install pydantic pytest pytest-asyncio

# 2. Run the test matrix in verbose mode
pytest test_assets.py -v