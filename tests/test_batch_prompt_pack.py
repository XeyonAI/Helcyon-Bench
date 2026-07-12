import sys
import tempfile
import types
import unittest
from pathlib import Path


streamlit = types.ModuleType("streamlit")


class SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


streamlit.session_state = SessionState()
components_pkg = types.ModuleType("streamlit.components")
components_v1 = types.ModuleType("streamlit.components.v1")
components_v1.html = lambda *args, **kwargs: None
streamlit.components = components_pkg
components_pkg.v1 = components_v1
sys.modules.setdefault("streamlit", streamlit)
sys.modules.setdefault("streamlit.components", components_pkg)
sys.modules.setdefault("streamlit.components.v1", components_v1)

import app as app_module  # noqa: E402
from app import (  # noqa: E402
    BATCH_SLOT_COUNT,
    HELCYON_COMPANION_V1_PROMPTS,
    INITIAL_PROMPT_PACK_PATH,
    apply_dashboard_model_aliases_to_score_entries,
    available_prompt_packs,
    benchmark_field_keys,
    batch_average_rows,
    batch_overall_scores,
    benchmark_session_payload,
    save_benchmark_session,
    import_benchmark_session,
    benchmark_winner_name,
    clear_response_inputs,
    has_visible_batch_input,
    load_dashboard_model_aliases,
    load_prompt_pack,
    load_helcyon_companion_v1_prompts,
    load_selected_prompt_pack,
    load_form_state,
    model_name_or_default,
    model_response_set_text,
    import_model_responses,
    import_model_responses_from_upload,
    hydrate_form_state,
    parse_model_response_metadata,
    parse_model_response_set,
    persist_current_form_state,
    prompt_pack_editor_entries,
    prompt_pack_filename,
    persisted_field_keys,
    remove_form_state,
    save_dashboard_model_aliases,
    save_form_state,
    save_model_response_set,
    save_prompt_pack,
    selected_prompt_pack_path,
    title_from_prompt,
    visible_prompt_pack_entries,
    visible_benchmark_items,
)
from llmbench.judge import CATEGORY_WEIGHTS  # noqa: E402


def result(score_a, score_b):
    return {
        "responses": {
            "A": {
                "overall": score_a,
                "scores": {category: score_a for category in CATEGORY_WEIGHTS},
            },
            "B": {
                "overall": score_b,
                "scores": {category: score_b for category in CATEGORY_WEIGHTS},
            },
        }
    }


class BatchPromptPackTests(unittest.TestCase):
    def test_initial_pack_has_enough_prompts_with_titles(self):
        self.assertIsNotNone(INITIAL_PROMPT_PACK_PATH)
        self.assertGreaterEqual(len(HELCYON_COMPANION_V1_PROMPTS), BATCH_SLOT_COUNT)
        for prompt in HELCYON_COMPANION_V1_PROMPTS:
            self.assertTrue(prompt["title"])
            self.assertTrue(prompt["prompt"])
            self.assertIn("id", prompt)
            self.assertIn("category", prompt)
            self.assertIn("evaluation_focus", prompt)

    def test_initial_pack_loads_from_editable_json_file(self):
        self.assertIsNotNone(INITIAL_PROMPT_PACK_PATH)
        loaded = load_prompt_pack(INITIAL_PROMPT_PACK_PATH)

        self.assertEqual(loaded, HELCYON_COMPANION_V1_PROMPTS)

    def test_available_prompt_packs_lists_json_files(self):
        packs = available_prompt_packs()

        self.assertTrue(packs)
        for path in packs.values():
            self.assertEqual(path.suffix, ".json")

    def setUp(self):
        streamlit.session_state.clear()

    def test_dashboard_model_aliases_round_trip_clean_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aliases.json"
            save_dashboard_model_aliases(
                {
                    "Fable": ["Fable v2", "Fable v1", "Fable v1", "Fable"],
                    "Empty": [],
                },
                path,
            )
            aliases = load_dashboard_model_aliases(path)

        self.assertEqual(aliases, {"Fable": ["Fable v1", "Fable v2"]})

    def test_dashboard_model_aliases_remap_score_entries_without_mutating_sources(self):
        entries = [
            {"model": "Fable v1", "category": "Overall", "score": 7.5},
            {"model": "Fable v2", "category": "Overall", "score": 8.5},
            {"model": "Northstar", "category": "Overall", "score": 8.0},
        ]

        remapped = apply_dashboard_model_aliases_to_score_entries(entries, {"Fable": ["Fable v1", "Fable v2"]})

        self.assertEqual([row["model"] for row in remapped], ["Fable", "Fable", "Northstar"])
        self.assertEqual(entries[0]["model"], "Fable v1")
        self.assertEqual(remapped[0]["original_model"], "Fable v1")

    def test_dashboard_switch_persists_and_rehydrates_visible_benchmark_fields(self):
        streamlit.session_state["model_name_a_input"] = "Fable v2"
        streamlit.session_state["model_name_b_input"] = "Fable v1"
        streamlit.session_state["batch_prompt_1"] = "Prompt before graph switch"
        streamlit.session_state["batch_response_a_1"] = "Response A before graph switch"
        streamlit.session_state["batch_response_b_1"] = "Response B before graph switch"

        with tempfile.TemporaryDirectory() as temp_dir:
            form_state_path = Path(temp_dir) / "form_state.json"
            persist_current_form_state(form_state_path)
            streamlit.session_state.clear()
            hydrate_form_state(form_state_path)

        self.assertEqual(streamlit.session_state["model_name_a_input"], "Fable v2")
        self.assertEqual(streamlit.session_state["model_name_b_input"], "Fable v1")
        self.assertEqual(streamlit.session_state["batch_prompt_1"], "Prompt before graph switch")
        self.assertEqual(streamlit.session_state["batch_response_a_1"], "Response A before graph switch")
        self.assertEqual(streamlit.session_state["batch_response_b_1"], "Response B before graph switch")

    def test_prompt_pack_loads_into_five_visible_prompt_slots(self):
        load_helcyon_companion_v1_prompts()

        self.assertEqual(BATCH_SLOT_COUNT, 5)
        self.assertEqual(streamlit.session_state["batch_prompt_1"], HELCYON_COMPANION_V1_PROMPTS[0]["prompt"])
        self.assertEqual(streamlit.session_state["batch_prompt_5"], HELCYON_COMPANION_V1_PROMPTS[4]["prompt"])
        self.assertEqual(streamlit.session_state["batch_response_a_1"], "")
        self.assertEqual(streamlit.session_state["batch_response_b_1"], "")

    def test_visible_prompt_entries_can_be_saved_as_simple_pack(self):
        streamlit.session_state["batch_prompt_1"] = "A fresh prompt for the pack."
        streamlit.session_state["batch_prompt_2"] = "Second prompt.\nWith detail."

        entries = visible_prompt_pack_entries()

        self.assertEqual(
            entries,
            [
                {"title": "A fresh prompt for the pack", "prompt": "A fresh prompt for the pack."},
                {"title": "Second prompt", "prompt": "Second prompt.\nWith detail."},
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pack.json"
            loaded = save_prompt_pack(entries, path)
            raw = path.read_text(encoding="utf-8")

        self.assertIn('"title": "A fresh prompt for the pack"', raw)
        self.assertEqual(loaded[0]["title"], "A fresh prompt for the pack")
        self.assertEqual(loaded[0]["id"], "prompt_01")

    def test_prompt_pack_filename_sanitizes_editor_name(self):
        self.assertEqual(prompt_pack_filename("My New Pack!"), "my-new-pack.json")
        self.assertEqual(prompt_pack_filename(""), "custom-prompt-pack.json")

    def test_prompt_pack_editor_entries_require_title_and_prompt(self):
        streamlit.session_state["pack_editor_title_1"] = "Title"
        streamlit.session_state["pack_editor_prompt_1"] = "Prompt"
        streamlit.session_state["pack_editor_title_2"] = "Missing prompt"

        with self.assertRaises(ValueError):
            prompt_pack_editor_entries()

        streamlit.session_state["pack_editor_title_2"] = ""
        self.assertEqual(prompt_pack_editor_entries(), [{"title": "Title", "prompt": "Prompt"}])

    def test_editor_fields_are_persisted_separately_from_benchmark_fields(self):
        self.assertIn("pack_editor_title_1", persisted_field_keys())
        self.assertIn("batch_prompt_1", benchmark_field_keys())
        self.assertNotIn("pack_editor_title_1", benchmark_field_keys())

    def test_editor_entries_can_overwrite_existing_pack_file(self):
        streamlit.session_state["pack_editor_title_1"] = "New Title"
        streamlit.session_state["pack_editor_prompt_1"] = "New prompt text."

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "existing.json"
            save_prompt_pack([{"title": "Old Title", "prompt": "Old prompt."}], path)
            save_prompt_pack(prompt_pack_editor_entries(), path)
            loaded = load_prompt_pack(path)

        self.assertEqual(loaded[0]["title"], "New Title")
        self.assertEqual(loaded[0]["prompt"], "New prompt text.")

    def test_selected_prompt_pack_uses_dropdown_value(self):
        label, path = next(iter(available_prompt_packs().items()))
        streamlit.session_state["prompt_pack_select"] = label

        self.assertEqual(selected_prompt_pack_path(), path)

    def test_selected_prompt_pack_load_clears_responses_and_populates_prompts(self):
        label, _ = next(iter(available_prompt_packs().items()))
        streamlit.session_state["prompt_pack_select"] = label
        for slot in range(1, BATCH_SLOT_COUNT + 1):
            streamlit.session_state[f"batch_response_a_{slot}"] = f"A {slot}"
            streamlit.session_state[f"batch_response_b_{slot}"] = f"B {slot}"

        load_selected_prompt_pack()

        self.assertEqual(streamlit.session_state["batch_prompt_1"], HELCYON_COMPANION_V1_PROMPTS[0]["prompt"])
        for slot in range(1, BATCH_SLOT_COUNT + 1):
            self.assertEqual(streamlit.session_state[f"batch_response_a_{slot}"], "")
            self.assertEqual(streamlit.session_state[f"batch_response_b_{slot}"], "")

    def test_title_from_prompt_falls_back_to_slot_name(self):
        self.assertEqual(title_from_prompt("", 3), "Prompt 3")

    def test_visible_benchmark_items_preserve_prompt_metadata(self):
        load_helcyon_companion_v1_prompts()
        for slot in range(1, BATCH_SLOT_COUNT + 1):
            streamlit.session_state[f"batch_response_a_{slot}"] = f"A {slot}"
            streamlit.session_state[f"batch_response_b_{slot}"] = f"B {slot}"

        items = visible_benchmark_items("Model A", "Model B")

        self.assertEqual(len(items), 5)
        self.assertTrue(has_visible_batch_input())
        self.assertEqual(items[0]["id"], "prompt_01")
        self.assertEqual(items[0]["category"], "")
        self.assertEqual(items[0]["title"], HELCYON_COMPANION_V1_PROMPTS[0]["title"])
        self.assertEqual(items[0]["evaluation_focus"], "")

    def test_visible_benchmark_items_preserve_manual_metadata_fallback(self):
        for slot in range(1, BATCH_SLOT_COUNT + 1):
            streamlit.session_state[f"batch_prompt_{slot}"] = f"Prompt {slot}"
            streamlit.session_state[f"batch_response_a_{slot}"] = f"A {slot}"
            streamlit.session_state[f"batch_response_b_{slot}"] = f"B {slot}"

        items = visible_benchmark_items("Model A", "Model B")

        self.assertEqual(len(items), 5)
        self.assertEqual(items[0]["id"], "prompt_01")
        self.assertEqual(items[0]["category"], "")
        self.assertEqual(items[0]["title"], "Prompt 1")
        self.assertEqual(items[0]["evaluation_focus"], "")

    def test_visible_benchmark_items_runs_only_complete_filled_entries(self):
        streamlit.session_state["batch_prompt_1"] = "Prompt 1"
        streamlit.session_state["batch_response_a_1"] = "A 1"
        streamlit.session_state["batch_response_b_1"] = "B 1"

        items = visible_benchmark_items("Model A", "Model B")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["current_prompt"], "Prompt 1")

    def test_visible_benchmark_items_defaults_blank_model_names(self):
        streamlit.session_state["batch_prompt_1"] = "Prompt 1"
        streamlit.session_state["batch_response_a_1"] = "A 1"
        streamlit.session_state["batch_response_b_1"] = "B 1"

        items = visible_benchmark_items("", "  ")

        self.assertEqual(items[0]["model_name_a"], "Model A")
        self.assertEqual(items[0]["model_name_b"], "Model B")

    def test_model_name_or_default_preserves_filled_names(self):
        self.assertEqual(model_name_or_default("A", " Helcyon "), "Helcyon")
        self.assertEqual(model_name_or_default("B", ""), "Model B")


    def test_export_filename_includes_prompt_pack_and_model_names(self):
        builder = None
        for name in (
            "benchmark_export_filename",
            "batch_export_filename",
            "export_filename",
            "export_report_filename",
            "report_filename",
        ):
            candidate = getattr(app_module, name, None)
            if callable(candidate):
                builder = candidate
                break

        self.assertIsNotNone(builder, "app.py must expose an export filename helper for regression coverage")

        call_attempts = (
            lambda: builder("json", "Helcyon 4o", "GPT-5.5", "Deep Conversation"),
            lambda: builder("Helcyon 4o", "GPT-5.5", "Deep Conversation", "json"),
            lambda: builder(
                export_type="json",
                model_name_a="Helcyon 4o",
                model_name_b="GPT-5.5",
                prompt_pack_name="Deep Conversation",
            ),
            lambda: builder(
                extension="json",
                model_name_a="Helcyon 4o",
                model_name_b="GPT-5.5",
                prompt_pack_name="Deep Conversation",
            ),
            lambda: builder(
                file_type="json",
                model_name_a="Helcyon 4o",
                model_name_b="GPT-5.5",
                prompt_pack_name="Deep Conversation",
            ),
        )

        filename = None
        last_error = None
        for attempt in call_attempts:
            try:
                filename = attempt()
                break
            except TypeError as exc:
                last_error = exc

        if filename is None:
            raise AssertionError(f"Export filename helper could not be called with supported signatures: {last_error}")

        self.assertTrue(filename.endswith(".json"))
        self.assertIn("helcyon", filename.lower())
        self.assertIn("deep-conversation", filename.lower())
        self.assertIn("helcyon-4o", filename.lower())
        self.assertIn("gpt-5-5", filename.lower())
        self.assertNotIn(" ", filename)

    def test_form_state_can_be_saved_loaded_and_partially_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "form_state.json"
            save_form_state({"batch_prompt_1": "Prompt", "batch_response_a_1": "A"}, path)

            self.assertEqual(load_form_state(path)["batch_prompt_1"], "Prompt")

            remove_form_state(["batch_response_a_1"], path)
            state = load_form_state(path)

        self.assertEqual(state, {"batch_prompt_1": "Prompt"})

    def test_model_response_set_text_round_trips_responses(self):
        responses = ["A 1", "A 2\nwith detail", "", "A 4", "A 5"]
        text = model_response_set_text("GPT-4o", "a", responses)

        self.assertIn("model: GPT-4o", text)
        self.assertEqual(parse_model_response_set(text), responses)
        self.assertEqual(parse_model_response_metadata(text)["model"], "GPT-4o")

    def test_import_model_responses_restores_model_name(self):
        responses = ["A 1", "A 2", "", "", ""]
        text = model_response_set_text("Northstar", "b", responses)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "northstar.txt"
            form_state_path = Path(temp_dir) / "form_state.json"
            path.write_text(text, encoding="utf-8")
            imported = import_model_responses(path, "b", form_state_path)
            form_state = load_form_state(form_state_path)

        self.assertEqual(imported, responses)
        self.assertEqual(streamlit.session_state["model_name_b_input"], "Northstar")
        self.assertEqual(form_state["model_name_b_input"], "Northstar")

    def test_import_model_responses_clears_stale_fresh_placeholder(self):
        streamlit.session_state["model_name_a_input"] = "Fresh A"
        responses = ["B 1", "", "", "", ""]
        text = model_response_set_text("Northstar", "b", responses)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "northstar.txt"
            form_state_path = Path(temp_dir) / "form_state.json"
            path.write_text(text, encoding="utf-8")
            import_model_responses(path, "b", form_state_path)

        self.assertEqual(streamlit.session_state["model_name_a_input"], "")
        self.assertEqual(streamlit.session_state["model_name_b_input"], "Northstar")

    def test_import_hwui_export_messages_with_prompt_response_rows(self):
        payload = {
            "schema": "helcyon_bench_hwui_export_v1",
            "model_name": "Helcyon GPT-4o",
            "messages": [
                {"index": 1, "prompt": "Prompt 1", "response": "Response 1"},
                {"index": 2, "prompt": "Prompt 2", "response": "Response 2"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            form_state_path = Path(temp_dir) / "form_state.json"
            imported = import_model_responses_from_upload(
                "hwui-export.json",
                app_module.json.dumps(payload).encode("utf-8"),
                "a",
                form_state_path,
            )
            form_state = load_form_state(form_state_path)

        self.assertEqual(imported[:2], ["Response 1", "Response 2"])
        self.assertEqual(streamlit.session_state["model_name_a_input"], "Helcyon GPT-4o")
        self.assertEqual(streamlit.session_state["batch_prompt_1"], "Prompt 1")
        self.assertEqual(streamlit.session_state["batch_response_a_1"], "Response 1")
        self.assertEqual(form_state["batch_prompt_2"], "Prompt 2")
        self.assertEqual(form_state["batch_response_a_2"], "Response 2")

    def test_benchmark_session_payload_saves_and_imports_whole_form(self):
        streamlit.session_state["prompt_pack_select"] = "Starter Philosophy"
        streamlit.session_state["prompt_pack_category_select"] = "Philosophy"
        streamlit.session_state["batch_prompt_1"] = "Prompt 1"
        streamlit.session_state["batch_response_a_1"] = "A 1"
        streamlit.session_state["batch_response_b_1"] = "B 1"
        metadata = {
            "name": "Starter Philosophy",
            "category": "Philosophy",
            "description": "A test pack",
            "judge_profile": "Philosophy",
        }
        payload = benchmark_session_payload("Model Alpha", "Model Beta", metadata)

        with tempfile.TemporaryDirectory() as temp_dir:
            session_path = Path(temp_dir) / "session.json"
            form_state_path = Path(temp_dir) / "form_state.json"
            saved_path = save_benchmark_session(payload, session_path)
            streamlit.session_state.clear()
            imported = import_benchmark_session(saved_path, form_state_path)
            form_state = load_form_state(form_state_path)

        self.assertEqual(imported["model_name_a"], "Model Alpha")
        self.assertEqual(streamlit.session_state["model_name_a_input"], "Model Alpha")
        self.assertEqual(streamlit.session_state["model_name_b_input"], "Model Beta")
        self.assertEqual(streamlit.session_state["batch_prompt_1"], "Prompt 1")
        self.assertEqual(streamlit.session_state["batch_response_a_1"], "A 1")
        self.assertEqual(streamlit.session_state["batch_response_b_1"], "B 1")
        self.assertEqual(form_state["last_prompt_pack_name"], "Starter Philosophy")
        self.assertEqual(form_state["prompt_pack_select"], "Starter Philosophy")

    def test_benchmark_session_rejects_empty_session(self):
        payload = {
            "model_name_a": "Model A",
            "model_name_b": "Model B",
            "prompt_pack": {"name": "Pack"},
            "slots": [{"slot": 1, "prompt": "", "response_a": "", "response_b": ""}],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                save_benchmark_session(payload, Path(temp_dir) / "empty.json")

    def test_model_response_set_saves_readable_txt_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "gpt-4o.txt"
            saved_path = save_model_response_set("GPT-4o", "a", ["A 1", "", "", "", ""], path)
            raw = saved_path.read_text(encoding="utf-8")

        self.assertEqual(saved_path.name, "gpt-4o.txt")
        self.assertIn("--- RESPONSE 1 ---", raw)
        self.assertEqual(parse_model_response_set(raw)[0], "A 1")

    def test_model_response_set_rejects_empty_responses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.txt"
            with self.assertRaises(ValueError):
                save_model_response_set("GPT-4o", "a", ["", " ", "", "", ""], path)

    def test_batch_average_rows_include_overall(self):
        rows = batch_average_rows(
            [
                {"result": result(8.0, 9.0)},
                {"result": result(10.0, 9.0)},
            ]
        )

        self.assertEqual(rows[0]["Response A Avg"], "9.00")
        self.assertEqual(rows[0]["Response B Avg"], "9.00")
        self.assertEqual(rows[-1]["Category"], "Overall")
        self.assertEqual(rows[-1]["Response A Avg"], "9.00")

    def test_benchmark_winner_uses_average_overall_scores(self):
        batch_results = [
            {
                "item": {"model_name_a": "Model A", "model_name_b": "Model B"},
                "result": result(9.0, 8.0),
            },
            {
                "item": {"model_name_a": "Model A", "model_name_b": "Model B"},
                "result": result(8.0, 9.5),
            },
        ]

        self.assertEqual(batch_overall_scores(batch_results), (8.5, 8.75))
        self.assertEqual(benchmark_winner_name(batch_results), "Model B")

    def test_clear_response_inputs_only_clears_selected_side(self):
        for slot in range(1, BATCH_SLOT_COUNT + 1):
            streamlit.session_state[f"batch_prompt_{slot}"] = f"Prompt {slot}"
            streamlit.session_state[f"batch_response_a_{slot}"] = f"A {slot}"
            streamlit.session_state[f"batch_response_b_{slot}"] = f"B {slot}"

        clear_response_inputs("a")

        for slot in range(1, BATCH_SLOT_COUNT + 1):
            self.assertEqual(streamlit.session_state[f"batch_prompt_{slot}"], f"Prompt {slot}")
            self.assertEqual(streamlit.session_state[f"batch_response_a_{slot}"], "")
            self.assertEqual(streamlit.session_state[f"batch_response_b_{slot}"], f"B {slot}")
        self.assertEqual(
            streamlit.session_state["clear_persistence_keys"],
            [f"batch_response_a_{slot}" for slot in range(1, BATCH_SLOT_COUNT + 1)],
        )


class PackRubricSelectionTests(unittest.TestCase):
    def test_explicit_rubric_field_wins_over_category(self):
        metadata = {"name": "Pack", "category": "Creativity", "rubric": "companion"}
        self.assertEqual(app_module.pack_rubric_filename(metadata), "companion.md")

    def test_rubric_field_is_case_insensitive_and_supports_custom_files(self):
        self.assertEqual(app_module.pack_rubric_filename({"rubric": "Companion"}), "companion.md")
        self.assertEqual(app_module.pack_rubric_filename({"rubric": "morals_v2"}), "morals_v2.md")

    def test_absent_rubric_field_falls_back_to_category_mapping(self):
        self.assertEqual(app_module.pack_rubric_filename({"category": "Creativity"}), "creativity.md")
        self.assertEqual(app_module.pack_rubric_filename({"category": "Philosophy"}), "philosophy.md")
        self.assertEqual(app_module.pack_rubric_filename({"category": "Morals"}), "morals.md")
        self.assertEqual(app_module.pack_rubric_filename({"category": "Uncensored"}), "uncensored.md")
        self.assertEqual(app_module.pack_rubric_filename({"category": "Humour"}), "humour.md")
        self.assertEqual(app_module.pack_rubric_filename({"category": "Companion"}), "companion.md")
        self.assertEqual(app_module.pack_rubric_filename({}), "companion.md")

    def test_category_rubric_files_exist_so_no_pack_silently_falls_back(self):
        rubrics = app_module.available_rubrics()
        for category in app_module.RUBRIC_FILENAME_BY_PACK_CATEGORY:
            path, warning = app_module.scoring_rubric_path_for_pack(
                rubrics, {"name": "Pack", "category": category}
            )
            self.assertEqual(path.name, app_module.RUBRIC_FILENAME_BY_PACK_CATEGORY[category])
            self.assertIsNone(warning)

    def test_missing_rubric_file_falls_back_to_companion_with_warning(self):
        rubrics = app_module.available_rubrics()
        metadata = {"name": "Pack", "category": "Creativity", "rubric": "does_not_exist"}
        path, warning = app_module.scoring_rubric_path_for_pack(rubrics, metadata)
        self.assertEqual(path.name, "companion.md")
        self.assertIn("does_not_exist.md", warning)

    def test_extra_categories_only_apply_with_matching_standalone_rubric(self):
        creativity = app_module.RUBRIC_DIR / "creativity.md"
        philosophy = app_module.RUBRIC_DIR / "philosophy.md"
        morals = app_module.RUBRIC_DIR / "morals.md"
        companion = app_module.RUBRIC_DIR / "companion.md"
        self.assertEqual(
            app_module.pack_extra_score_categories({"category": "Creativity"}, creativity),
            ["Creativity"],
        )
        self.assertEqual(
            app_module.pack_extra_score_categories({"category": "Philosophy"}, philosophy),
            ["Philosophical Depth"],
        )
        self.assertEqual(
            app_module.pack_extra_score_categories({"category": "Morals"}, morals),
            ["Moral Reasoning"],
        )
        # A category that fell back to companion.md must not request its category.
        self.assertEqual(app_module.pack_extra_score_categories({"category": "Creativity"}, companion), [])
        self.assertEqual(app_module.pack_extra_score_categories({"category": "Companion"}, companion), [])

    def test_distress_addendum_appended_for_empathy_and_signalled_packs(self):
        creativity = app_module.RUBRIC_DIR / "creativity.md"
        companion = app_module.RUBRIC_DIR / "companion.md"
        base = app_module.load_text(companion)
        # Non-distress pack: primary rubric only.
        self.assertEqual(
            app_module.scoring_rubric_text_for_pack(companion, {"category": "Companion"}),
            base,
        )
        # Empathy category triggers the addendum.
        empathy_text = app_module.scoring_rubric_text_for_pack(companion, {"category": "Empathy"})
        self.assertTrue(empathy_text.startswith(base))
        self.assertIn("Distress Calibration", empathy_text)
        # Description signalling distress triggers it even off a different rubric.
        signalled = app_module.scoring_rubric_text_for_pack(
            creativity, {"category": "Creativity", "description": "prompts about grief and loss"}
        )
        self.assertTrue(signalled.startswith(app_module.load_text(creativity)))
        self.assertIn("Distress Calibration", signalled)

    def test_rubric_field_survives_pack_load_and_metadata_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack_path = Path(tmp) / "custom_pack.json"
            pack_path.write_text(
                '{"name": "Custom", "category": "Companion", "rubric": "companion", '
                '"prompts": [{"title": "T", "prompt": "P"}]}',
                encoding="utf-8",
            )
            document = app_module.load_prompt_pack_document(pack_path)
        self.assertEqual(document["rubric"], "companion")
        normalized = app_module.normalize_prompt_pack_metadata(document)
        self.assertEqual(normalized["rubric"], "companion")
        self.assertEqual(app_module.pack_rubric_filename(normalized), "companion.md")


if __name__ == "__main__":
    unittest.main()
