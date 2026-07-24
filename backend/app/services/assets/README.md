# Asset Service & Visual Quality Pipeline — Sprint 2 Documentation

## 1. Overview
The `AssetService` module is responsible for resolving textual visual cues generated during scene planning into optimized visual prompts, validating output quality, and persisting asset metadata[cite: 1].

In Sprint 2, the pipeline was updated to use **CrewAI**'s native `LLM` wrapper connected to the `kimi-k2.5` model via LiteLLM proxy, ensuring stability, strict style adherence, and automated quality validation.

---

## 2. Visual Quality Criteria & Prompt Refinement

### 2.1 Quality Standards
To maintain a consistent, professional, MOOC-style educational aesthetic[cite: 1], generated visual assets must adhere to specific constraints:

* **Required Style Elements:** Prompts must explicitly contain style descriptors including `"flat 2d"` and `"illustration"`[cite: 1].
* **Forbidden Elements:** Prompts must avoid text overlays, 3D renders, photorealistic textures, drop shadows, watermarks, and complex color gradients[cite: 1].

### 2.2 Automated Quality Evaluation Logic
Quality evaluation is handled programmatically via `_evaluate_prompt_quality(prompt: str)`:

1. **Required Keyword Check:** Verifies that all terms in `REQUIRED_STYLE_KEYWORDS` are present in the lowercase prompt.
2. **Negation-Aware Forbidden Keyword Check:** Checks for `FORBIDDEN_PROMPT_KEYWORDS` using negative lookbehind regular expressions:
   ```regex
   (?<!no\s)\b{keyword}\b

```

* **Valid Constraint:** `"flat 2d illustration, no text, no shadows"` $\rightarrow$ **PASS** (The words "text" and "shadows" are preceded by `"no "`).
* **Forbidden Artifact:** `"flat 2d illustration with drop shadow"` $\rightarrow$ **FAIL** (Contains standalone forbidden term).

---

## 3. Data Schema & Integration Contract

### 3.1 AssetItem Schema

Every asset generated or resolved by `AssetService` strictly follows the `AssetItem` contract with full license and metadata traceability:

| Field | Type | Description |
| --- | --- | --- |
| `asset_id` | `str` | Unique identifier for the asset (e.g., `"image_1"`). |
| `scene_reference` | `str` | ID of the scene containing this element.

 |
| `cue_reference` | `str` | ID of the prompt cue triggering the asset. |
| `asset_type` | `str` | Type of asset (e.g., `"image"`, `"diagram"`, `"icon"`).

 |
| `url` | `str` | Storage URI or download location. |
| `prompt` | `str` | Refined LLM generation prompt. |
| `source` | `str` | Origin of the asset (e.g., `"generated"`, `"searched"`).

 |
| `asset_license` | `str` | Licensing status (e.g., `"open-source"`, `"license-cleared"`).

 |
| `element` | `str` | Original raw visual cue description. |

---

## 4. Animation Engine Compatibility (Youssef Integration)

To guarantee seamless integration with Youssef's Animation & Search Engine, `process_scene_elements` outputs a clean JSON structure mapping scene IDs directly to asset references:

### 4.1 Downstream Output Contract (`process_scene_elements`)

```json
{
  "video_id": "video_test_123",
  "assets": `https://supabase-storage.local/assets/e5b3f11c-....png`",
      "type": "image",
      "license": "open-source",
      "source": "generated"
    }
  ]
}

```

---

## 5. Persistence & Storage

* Asset entries are recorded in `data/supabase_asset_metadata.json` upon successful resolution.
* Safe file handling ensures automatic directory creation and structured JSON append operations.

---

## 6. Verification & Test Suite

The asset service includes unit and integration coverage in `backend/tests/test_assets.py`:

* **Unit Tests:** `TestAssetServiceQualityEvaluation` verifies regex negation logic and keyword enforcement without network overhead.
* **Integration Tests:** `test_process_scene_elements_success` verifies full pipeline processing and fallback handling using mocked dependencies.