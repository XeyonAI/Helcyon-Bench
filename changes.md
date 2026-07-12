# Changes

## 2026-07-09

- Added a Judge column to the model card "ⓘ" details modal showing which judge model scored each saved run (read from the benchmark JSON's judge_model field, with the .gguf extension trimmed; older files without it show "Unknown").
- Redesigned the judging progress overlay: animated flowing-gradient border and title, spinner, live percentage readout, rainbow gradient progress fill with a shimmer sweep, and per-prompt step dots (green when done, pulsing amber for the prompt being judged). Same overlay element IDs, so progress updates and the Stop flow are unchanged.
- Registered seven missing judging profiles (Creativity, Coding, Editing, Morals, Philosophy, Planning, Reasoning) with dedicated judge instructions, plus lookup aliases. Their starter packs previously fell back to generic profile guidance with a "not a registered judging profile" warning; every prompt pack's judge_profile now resolves to a real profile. Creativity, Morals, and Philosophy instructions are distilled from their rubric files.
- Fixed benchmark form fields going blank after visiting the Results Dashboard: Streamlit drops session state for widgets that are not rendered on the current view, so the dashboard now re-registers every benchmark field (model names, prompts, responses, pack editor, prompt pack selection) as programmatic state each run, keeping values alive until their widgets render again. Fields now survive view switches in-session without needing a refresh; the clear buttons remain the only way to empty them.

## 2026-07-08

- Added benchmark run dates across the Results Dashboard: each model card gained an "ⓘ" button next to Trend that opens a details modal listing every saved run's date, benchmark pack, and category (a home for more per-model info later), the per-prompt winners table gained a Date column, Model A vs B trend rows show the run date, and the trend dialog's Run column shows a readable date and time.
- Fixed the jarring page shift when ticking "Include in consolidation": the selection summary line under the consolidate controls is now always rendered (with instructions when nothing is selected), so the card grid no longer jumps under the cursor.
- Added a Clear Selection button next to Confirm Consolidate that unticks every consolidation checkbox in one click, and the confirm button now shows how many models are selected.
- Added a Date dropdown to the dashboard filter row (Ignore dates / Newest to oldest / Oldest to newest) that orders model cards by their most recent run date, with the Sort dropdown breaking ties.
- Bottom-aligned the Confirm Consolidate and Clear Selection buttons with the "Consolidate selected as" name field.
- Relabelled the cryptic "↗" model-card button to "Trend ↗" with a clearer tooltip.
- Moved the model-card Delete button from the cramped top action row (where its label wrapped) to the card's bottom-right, opposite the consolidation checkbox, wide enough for the label; the delete confirmation now appears in the same spot.

## 2026-07-06

- Fixed encoding damage in `rubrics/companion.md` (58 corrupted bullet characters and a byte-order mark were being sent to the judge on every run) and renamed its category headings to match the schema's exact keys (Conversational Restraint to Restraint, Humour Participation to Humour).
- Added per-pack rubric selection: packs may declare an explicit `"rubric"` field (`"companion"` / `"extended"`, or a custom rubric filename stem); without it, Creativity, Philosophy, and Morals packs use `companion_extended.md` and all others use `companion.md`. A missing rubric file warns visibly and falls back to `companion.md`.
- Added three optional score categories (Creativity, Philosophical Depth, Moral Reasoning) that become required alongside the mandatory six when a pack's category activates them and the extended rubric is loaded; the JSON schema, llama.cpp grammar, output instructions, validation, and report/table rendering all extend dynamically. Prompts for the base six categories are byte-identical to before.
- Fixed report provenance: `Rubric:` in saved reports and the `rubric` field in benchmark JSON now record the actual rubric filename used instead of repeating the judge profile name.
- Unregistered judge profile names now show a visible warning instead of silently sending the judge generic guidance.

- Renamed the Safety test category to Uncensored and replaced `starter_safety_v1.json` with `starter_uncensored_v1.json`, which holds five new prompts testing direct engagement with edgy or controversial topics without hedging, lecturing, or refusing; the pack now uses the Judgement judge profile (the old Safety profile name never existed and silently fell back to General). No saved benchmark results referenced the Safety category, so no data migration was needed.

- Added a `judge.debug_logging` config option (default `true`); setting it to `false` stops all judge debug JSONL writes to `judge_logs/` while leaving judging behaviour unchanged.
- Added a `.gitignore` and removed `.venv`, `__pycache__`, `config.yaml`, `.llmbench_form_state.json`, archived model responses, and `Helcyon-Bench.rar` from git tracking; local files remain on disk.
- Pinned `streamlit`, `requests`, and `PyYAML` versions in `requirements.txt` to the tested versions.
- Deleted the obsolete `tests/test_batch_prompt_pack_old.py`, which targeted removed prompt-pack APIs and produced all failing tests.

- Added temporary local-judge pipeline debug logging to `judge_logs/judge_pipeline_debug.jsonl` for prompt construction, llama.cpp request payloads, raw model output, JSON extraction, repair output, parsed objects, and exported benchmark JSON snapshots.
- Tightened local judge JSON-output instructions and schema descriptions so judges paraphrase referenced phrases instead of quoting inside JSON strings, keep string values complete, and avoid splitting fragments across array entries; expanded repair logs with parse errors plus original/repaired excerpts.
- Added a local-judge JSON recovery step that strips diagnostic response-format labels and `<|im_end|>`, extracts the first JSON object, and conservatively repairs unescaped quotes inside string values with explicit repair-attempt logging.
- Moved Benchmark Strength Map delete confirmation into the selected model card and made failed deletes report explicitly when no files were removed.
- Moved Benchmark Strength Map card actions below the title so trend/delete controls no longer crowd the overall score or push it off the card.
- Added internal bottom padding to Benchmark Strength Map cards so the final graph bar has breathing room above the card border.
- Replaced the failed right-click dashboard delete menu with a visible compact red delete button on each Benchmark Strength Map model card, keeping the explicit confirmation step.
- Restored Benchmark Strength Map graph boxes using real Streamlit bordered containers so the compact trend button no longer breaks card backgrounds, borders, or padding.
- Fixed the Benchmark Strength Map trend icon so it is a real compact Streamlit button again instead of a hidden-trigger HTML shim.
- Fixed the Benchmark Strength Map regression by removing dashboard form persistence entirely, restoring compact no-refresh trend icon controls in model-card headers, hiding their native trigger buttons, and restoring vertical spacing between graph cards.

## 2026-07-05

- Stopped the Results Dashboard from running the benchmark form browser-persistence injector, so visiting graphs cannot overwrite prompt/response fields with absent or blank widget state before returning to Benchmark Test.
- Hardened Local judge response-format fallback so empty-body HTTP 400/422 and connection-aborted failures from json_schema/json_object modes retry the next mode instead of ending the judge run, with explicit fallback-attempt logging.
- Fixed the Judge button state after completed runs by rerendering out of the pulsing state, changed completed unchanged inputs to show Retest, and darkened the judging/edit orange styling.
- Aligned import buttons with adjacent labelled upload/select controls so the main response import, saved-response import, and saved-session import rows no longer sit too high.
- Added action-colored buttons: Judge is green, Judging pulses yellow, Delete buttons are red, Save buttons are green, and edit/editor/rename actions use a muted orange.
- Moved HWUI test-chat importing out of the Prompt Pack Editor and into the main benchmark setup, adding a Model A / Model B target selector and support for importing chat-style JSON directly into the chosen response column.
- Added Prompt Pack Editor import support for HWUI / Helcyon-Bench JSON exports, accepting direct prompt-pack JSON or wrapped `prompt_pack` payloads, saving imported packs into prompt_packs with collision-safe filenames, selecting the new pack, and loading it into the editor.
- Made judge response parsing accept whitespace-trimmed, fenced, and embedded JSON objects before declaring non-JSON failure, while logging byte-for-byte raw assistant content and parse exceptions for failed parse attempts.
- Expanded non-200 judge request logs with status code, response text, response headers, response-format mode, prompt id, and prompt length, and made 400 responses fall back from json_schema to json_object to no response_format.
- Added per-attempt judge request lifecycle logging before endpoint calls, including prompt id, judge model, endpoint, timeout, token limits, temperature, response-format mode, prompt character length, and completed/timed-out/errored outcomes.
- Replaced Results Dashboard trend graph URL links with native app buttons so trend modals open without browser navigation or blank-page refreshes, while still clearing stale trend modal state when leaving the dashboard.
- Added a sidebar Test Judge Connection button that reuses the benchmark preflight path to check /v1/models and a tiny structured /v1/chat/completions request before starting a judging run.
- Added deterministic judge verdict consistency handling: raw judge output and parsed results are logged to judge_logs, score-derived winners are checked against clear A/B final_verdict wording, mismatches repair winner.response with an explicit warning, exports now include winner.model_name, and user backups include judge logs.
- Clarified the split between benchmarks report exports and benchmark_sessions reloadable snapshots, filtered saved-session imports so report JSON files cannot appear as reloadable sessions, and fixed run/report metadata to prefer the prompt pack matched by the visible prompts instead of a potentially stale prompt-pack dropdown.
- Reconfigured the old HWUI backup batch files for Helcyon-Bench, producing separate zip archives for portable app files and local user files such as prompt packs, benchmark results, saved sessions, model responses, config, and form state.
- Added a Windows Setup.bat plus requirements.txt and README setup note so copied Helcyon-Bench folders can create or rebuild their local .venv, install dependencies, and seed config.yaml from the example config.
- Added a judging-in-progress interaction shield so accidental page clicks cannot interrupt a running benchmark, while Streamlit's top Stop button remains available for deliberate cancellation.
- Fixed prompt-pack category switching so the selected category controls the pack list instead of a stale pack label overriding it, and classified humour-named packs as Humour even if stale metadata says Companion.
- Added a built-in Starter Companion fallback so the Companion category still appears if the JSON file is missing or the prompt_packs folder is temporarily write-blocked.
- Made action toasts one-shot by clearing saved status messages after display, and cleared stale save/import toasts when refreshing judge models so old save notifications do not replay on unrelated reruns.

## 2026-07-04

- Changed Save As New Pack into a two-step flow that reveals a New Pack Name field plus Create New Pack/Cancel buttons, and relabelled in-place saving as Save / Rename Selected Pack.
- Simplified Prompt Pack Editor saving to two clear actions: Update Selected Pack for in-place edits and Save As New Pack for creating a separate pack, removing the redundant Rename Selected Pack button.
- Replaced large inline action status banners with short toast-style notifications so save/delete/rename/import feedback no longer shifts the page layout.
- Removed the confusing Use Visible Prompts button from the Prompt Pack Editor so editor population now uses the clearer Load Selected Pack Into Editor action.
- Removed the redundant top-level Save Visible Prompts To Pack button so prompt-pack saving now flows through the Prompt Pack Editor controls.
- Fixed Rename Selected Pack so it updates the selected pack's display metadata in place instead of trying to rename the underlying JSON file, and made Save As treat underscores as separators to avoid collision-prone filenames.
- Restored Companion as the active/default prompt-pack category, kept General separate, inferred categories for legacy packs from filename/profile metadata, and added prompt-pack Delete, Save Current Pack As, and Rename Selected Pack controls.
- Added an explicit active test summary beside Benchmark Prompts showing Test Category, Active Pack, and Judge Profile, and fixed prompt-pack selector indexes so they reflect the active session state instead of visually falling back to defaults.
- Audited app button feedback and moved Save All / Import All / folder-open status messages out of the collapsed saved-files expander, with clean success/error reporting for saved-session actions.
- Made Model Response save/import feedback visible outside the collapsed file expander, with success/error styling and automatic expander reopening after a response-file action.
- Fixed the remaining Results Dashboard return-path bug by rehydrating blank Streamlit widget state from the saved form file on every rerun, so protected responses come back into the visible fields after switching views.
- Hardened benchmark form persistence so blank Streamlit rerun snapshots from switching to the Results Dashboard cannot wipe already-saved prompts, model names, or responses unless a clear button explicitly requested it.
- Added full benchmark session Save All / Import All support, storing model names, prompt-pack metadata, five prompts, and both response columns together for quick model-combination reloads.
- Fixed model-response imports so the saved `model:` header restores the target Model Name field, persists it with the imported responses, and clears stale `Fresh A` / `Fresh B` placeholders from older form state.
- Fixed benchmark form persistence so refreshes and switching to the Results Dashboard do not overwrite saved model, prompt, or response fields unless a clear button is used.
- Moved per-model trend graph triggers into each Results Dashboard model card header and kept the popup graph tied to the clicked model under the active filters.
- Added Results Dashboard filters for benchmark category, model selection, score-category view, and highest/lowest/model-name sorting so only the selected result slice is shown.
- Moved the Benchmark Strength Map behind a separate Results Dashboard view, keeping the main benchmark test form clean, and fixed its generated HTML so it renders as cards and bars instead of visible code.
- Added a Benchmark Strength Map that reads saved JSON results from the benchmarks folder and renders colourful per-model category bars, average category scores, per-prompt winners, confidence, score differences, and Model A vs B trend bars.
- Revised local judge endpoints so `Local` uses the shared HWUI llama.cpp server on `http://127.0.0.1:5000/v1` by default, while `Local Dedicated` remains available on `5001` as an optional advanced endpoint.
- Added Bench-side shared-server signalling with `X-HelcyonBench-Run: true`, optional lock/unlock lifecycle hooks, and `/v1/models` plus tiny structured chat preflight checks before benchmark runs.
- Enforced structured local judge output by trying JSON schema, then JSON object mode, then llama.cpp grammar, without falling back to prose-only requests.
- Exposed a Local judge endpoint in config.yaml, added sidebar model refresh from `/v1/models`, and documented switching between local and OpenAI judges.
- Added a sidebar Judge selector backed by configured API models and added GPT-5.5 beside GPT-4o in the OpenAI judge model list.
- Added the selected prompt-pack name to saved model response filenames alongside the broad category, so response files identify the exact test set they came from.

## 2026-07-03

- Added a one-time larger-token retry when judge responses end empty with finish_reason length, and raised OpenAI example/local judge token limits from 1200 to 4800.
- Changed empty judge API messages into explicit endpoint errors that preserve finish_reason and the raw API response for the Raw judge response panel.
- Made raw judge-response debugging appear even for empty judge replies and preserved text-part response content from chat endpoints before JSON parsing.
- Made judge JSON parsing tolerate Markdown fences and explanatory text around the first complete JSON object, with raw judge output shown in an expander when parsing still fails.
- Replaced the obsolete sidebar Rubric dropdown with a read-only active Judge Profile display and made benchmark labels follow the selected Prompt Pack metadata.
- Remembered the last loaded or run prompt-pack category across restarts and used it when saving model response files, so filenames no longer fall back to General after reopening Helcyon-Bench.
- Added the selected prompt-pack category to saved model response filenames so response sets show which benchmark category they were used with.
- Automatically saves completed benchmark Markdown and JSON exports into the local benchmarks folder and adds an Open Benchmarks Folder button beside export controls.
- Fixed prompt-pack metadata propagation so benchmark runs, reports, and JSON exports use the selected pack name, category, and judge_profile instead of falling back to General.
- Added support for named judge endpoints so the sidebar can switch between cloud and local OpenAI-compatible judge models.
- Updated the launcher to clean up workspace-scoped Streamlit/app.py processes before and after a run while leaving Streamlit's normal file-watcher refresh behaviour enabled.
- Added starter template prompt packs for Companion, Deep Conversation, Morals, Creativity, Philosophy, Roleplay, Humour, Coding, Editing, Planning, Reasoning, Safety, and General.
- Simplified the Prompt Pack Editor so the visible metadata editing is just Category plus the prompt titles/questions, with Judge Profile saved automatically from Category.
- Added metadata-driven prompt-pack organisation with category-filtered pack selection and editor controls for pack name, category, description, and judge profile.
- Defaulted legacy prompt packs without metadata to General category, blank description, and General judge profile while preserving backwards-compatible loading.
- Added support for prompt-pack metadata objects with name, category, description, judge_profile, and prompts fields.
- Fixed duplicate success banners after saving from the Prompt Pack Editor.
- Added judging profiles for Companion, Deep Conversation, Humour, Roleplay, Admin, and Judgement, with prompt-pack selection automatically feeding the chosen judging philosophy into the judge prompt.
- Added Judge Profile metadata to benchmark Markdown and JSON exports while keeping the existing scoring categories unchanged.
- Added backward-compatible prompt-pack profile loading so existing array-shaped packs still work, with filename-based profile inference and explicit judging_profile metadata for newly saved packs.
- Renamed the app UI and generated user-facing labels from LLM-Bench to Helcyon-Bench.
- Moved copy/paste controls onto the field header row above each input and aligned the prompt-pack dropdown with its action buttons.
- Removed the duplicate prompt-pack editor save notification so only one banner appears after saving.
- Made prompt-pack editor saves explicit and visible with a primary Save Current Pack button, success/error banners, and a clearer Save Visible Prompts To Pack label.
- Renamed the benchmark prompt save button to Save Visible Prompts, added Save Editor To Selected Pack, and persisted prompt-pack editor drafts to avoid losing edited pack work.
- Added a Prompt Pack Editor section for loading/editing pack titles and prompts, using visible prompts as a starting point, and saving a new non-overwriting JSON pack.
- Added model response file saving and importing so a saved Model A or Model B response set can be reused against another model later.
- Added app-side form state persistence so model names, prompts, and responses survive browser refreshes and duplicated tabs until cleared.
- Replaced the hidden copy/paste overlay with visible compact clipboard buttons above each model, prompt, and response field.
- Made field persistence find Streamlit widgets by visible label first so model, prompt, and response text survives browser refresh more reliably.
- Hardened prompt-pack startup so the app falls back to the first available prompt pack if the old default pack filename is not present.
- Added a Judge-time warning when either model name field is blank, while defaulting blank labels to Model A and Model B.
- Added discreet per-field copy and paste controls to model, prompt, and response inputs.
- Replaced the single Helcyon prompt-load button with prompt-pack selection, Load Selected Pack, and Save Current Pack controls.
- Added support for selecting and saving multiple JSON prompt packs from prompt_packs, with saved packs containing only title and prompt entries.
- Renamed response clearing controls to Clear Model A Responses, Clear Model B Responses, and Clear All Benchmark Inputs.
- Updated benchmark item collection so judging runs all complete filled prompt entries while preserving the unified five-prompt UI.
- Added separate Clear Response A and Clear Response B buttons for retesting one model while keeping the other side intact.
- Restored an at-a-glance benchmark winner header with final overall scores for both models.
- Changed the button and accent styling from bright green to a darker faded blue.
- Added a "Save Visible Prompts to Pack" button that writes the five visible prompt boxes back to the editable JSON prompt pack.
- Simplified prompt pack JSON so only title and prompt are required; metadata fields are optional.
- Moved Helcyon Companion v1 prompts into editable prompt_packs/helcyon_companion_v1.json.
- Updated the app to load the prompt pack from disk so prompts can be edited or swapped without changing Python code.
- Added built-in Helcyon Companion v1 prompt pack with 10 companion-evaluation prompts.
- Added guarded "Load Helcyon Companion v1 Prompts" action that asks before replacing visible prompt fields.
- Added averaged category summaries across benchmark results while retaining per-prompt category score tables.
- Replaced JSON input with five visible Prompt / Response A / Response B prompt sections.
- Added timestamped export filenames using sanitized Response A and Response B model names.
- Added localStorage-backed benchmark form persistence for model labels, visible prompts, responses, rubric selection, and judge model selection.
- Added a confirmed Clear / Reset flow that clears persisted benchmark inputs without clearing existing results.
- Consolidated judging into one five-prompt benchmark workflow and removed the separate single-comparison form.

## 2026-07-02

- Tightened judge prompt and companion rubric to forbid N/A category scores.
- Improved non-numeric score validation errors so N/A failures identify the response and category.
- Added unittest coverage for numeric score validation and clear N/A rejection.
- Added support for both max_tokens and max_completion_tokens in judge API requests.
- Added automatic one-time retry between token limit parameter names when an endpoint rejects one as unsupported.
- Added clearer token-parameter failure reporting when both compatible forms fail.
- Updated config.example.yaml to prefer max_completion_tokens while documenting max_tokens for local endpoints.

## 2026-07-01

- Changed judging methodology to examiner-style independent marking before comparison.
- Moved overall score, winner, confidence, and score differences into application-side calculation from category scores.
- Added per-category deduction notes to the judge schema and comparison report.
- Added a score summary table for category-by-category A/B differences and overall difference.
- Converted the app from single-response judging to side-by-side response comparison.
- Added optional conversation context, current prompt, Response A/B inputs, and optional model-name labels.
- Updated judge output validation for winner, confidence, independent A/B scores, comparison answers, and final verdict.
- Updated the companion rubric and default judging prompt so direct comparison is the primary task.
- Updated Markdown and JSON exports for comparison reports.
- Updated README workflow notes for the new comparison-focused app.
- Built the initial standalone LLM-Bench Streamlit application.
- Added OpenAI-compatible judge API support with YAML configuration.
- Added the default companion-response rubric and JSON result validation.
- Added Markdown report export, JSON export, clear control, and lightweight session history.
- Added setup and usage documentation plus a Windows launcher.
- Added a fallback for OpenAI-compatible endpoints that reject `response_format`.
