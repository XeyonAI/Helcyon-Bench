import json
import unittest
from unittest.mock import patch

from llmbench.api import ChatCompletionResult, structured_output_payloads
from llmbench.config import AppConfig, JudgeConfig, JudgeEndpointConfig
from llmbench.judge import (
    CATEGORY_WEIGHTS,
    JUDGE_OUTPUT_SCHEMA,
    JudgeError,
    OPTIONAL_CATEGORY_WEIGHTS,
    OUTPUT_INSTRUCTIONS,
    judge_comparison,
    judge_output_grammar,
    judge_output_schema,
    output_instructions,
    parse_json,
    scoring_categories,
    validate_result,
)


def response(scores, categories=None):
    return {
        "scores": scores,
        "strengths": ["Clear conversational strength."],
        "deductions": {category: "No meaningful deduction." for category in (categories or CATEGORY_WEIGHTS)},
        "weaknesses": [],
    }


def result_with(scores_a, scores_b, categories=None):
    return {
        "responses": {
            "A": response(scores_a, categories),
            "B": response(scores_b, categories),
        },
        "comparison": {
            "more_natural": "Response A and Response B are both marked numerically.",
            "better_frame_following": "The higher score reflects the category marks.",
            "stronger_emotional_presence": "The category marks determine this.",
            "better_evidence_discipline": "The category marks determine this.",
            "better_conclusion": "The category marks determine this.",
            "more_enjoyable": "The category marks determine this.",
            "weaknesses": "Weaknesses are reflected in deductions.",
        },
        "final_verdict": "The winner is calculated from numeric category scores.",
    }


class JudgeValidationTests(unittest.TestCase):
    def test_numeric_scores_pass(self):
        scores_a = {category: 8.5 for category in CATEGORY_WEIGHTS}
        scores_b = {category: 9.0 for category in CATEGORY_WEIGHTS}

        result = validate_result(result_with(scores_a, scores_b))

        self.assertEqual(result["responses"]["A"]["overall"], 8.5)
        self.assertEqual(result["responses"]["B"]["overall"], 9.0)
        self.assertEqual(result["winner"]["response"], "B")

    def test_na_score_is_rejected_clearly(self):
        scores_a = {category: 8.5 for category in CATEGORY_WEIGHTS}
        scores_b = {category: 9.0 for category in CATEGORY_WEIGHTS}
        scores_a["Humour"] = "N/A"

        with self.assertRaises(JudgeError) as raised:
            validate_result(result_with(scores_a, scores_b))

        message = str(raised.exception)
        self.assertIn("response A Humour", message)
        self.assertIn("Scores must be numeric", message)
        self.assertIn("never return N/A", message)

    def test_local_judge_repairs_unescaped_quotes_inside_string_values(self):
        raw = """[json_object]
{
  "responses": {
    "A": {
      "scores": {
        "Emotional Presence": 8,
        "Conversation Flow": 8,
        "Evidence Discipline": 8,
        "User Frame Following": 8,
        "Humour": 8,
        "Restraint": 8
      },
      "strengths": ["Clear."],
      "deductions": {
        "Emotional Presence": "No meaningful deduction.",
        "Conversation Flow": "No meaningful deduction.",
        "Evidence Discipline": "No meaningful deduction.",
        "User Frame Following": "No meaningful deduction.",
        "Humour": "No meaningful deduction.",
        "Restraint": "No meaningful deduction."
      },
      "weaknesses": []
    },
    "B": {
      "scores": {
        "Emotional Presence": 7,
        "Conversation Flow": 7,
        "Evidence Discipline": 7,
        "User Frame Following": 7,
        "Humour": 7,
        "Restraint": 7
      },
      "strengths": ["Clear."],
      "deductions": {
        "Emotional Presence": "No meaningful deduction.",
        "Conversation Flow": "No meaningful deduction.",
        "Evidence Discipline": "No meaningful deduction.",
        "User Frame Following": "No meaningful deduction.",
        "Humour": "No meaningful deduction.",
        "Restraint": "No meaningful deduction."
      },
      "weaknesses": []
    }
  },
  "comparison": {
    "more_natural": "Response A separates the loyalty question from the "assistant to a harmful situation" question more clearly.",
    "better_frame_following": "Response A follows the frame.",
    "stronger_emotional_presence": "Response A is warmer.",
    "better_evidence_discipline": "Response A is cleaner.",
    "better_conclusion": "Response A concludes better.",
    "more_enjoyable": "Response A is more enjoyable.",
    "weaknesses": "Response B is flatter."
  },
  "final_verdict": "Response A wins."
}
<|im_end|>"""

        with patch("llmbench.judge.log_judge_event") as log_event:
            parsed = parse_json(raw)

        self.assertIn('"assistant to a harmful situation"', parsed["comparison"]["more_natural"])
        self.assertEqual(parsed["final_verdict"], "Response A wins.")
        repair_logs = [
            call.args[1]
            for call in log_event.call_args_list
            if call.args[0] == "judge_json_repair_parse"
        ]
        self.assertTrue(repair_logs)
        self.assertIn("Expecting ',' delimiter", repair_logs[0]["parse_error"])
        self.assertIn('\\"assistant to a harmful situation\\"', repair_logs[-1]["repaired_error_excerpt"])
        self.assertIn(
            '"assistant to a harmful situation"',
            repair_logs[-1]["original_error_excerpt"],
        )
        self.assertTrue(repair_logs[-1]["embedded_quote_recovery_attempted"])

    def test_judge_prompt_and_schema_discourage_inner_quotes_and_fragments(self):
        expected_lines = [
            "Do not use quotation marks inside JSON string values.",
            "When referring to words or phrases from a response, paraphrase them instead of quoting them.",
            "Keep every string value as one complete sentence or phrase.",
            "Do not split a sentence fragment across multiple array entries.",
        ]
        for line in expected_lines:
            self.assertIn(line, OUTPUT_INSTRUCTIONS)

        description = JUDGE_OUTPUT_SCHEMA["properties"]["final_verdict"]["description"]
        self.assertIn("Do not use quotation marks inside JSON string values", description)
        strengths_description = JUDGE_OUTPUT_SCHEMA["$defs"]["response"]["properties"]["strengths"][
            "description"
        ]
        self.assertIn("complete sentence or phrase", strengths_description)

    def test_local_structured_output_prefers_json_object_before_json_schema(self):
        schema = {"type": "object", "properties": {}, "additionalProperties": False}

        default_modes = [name for name, _ in structured_output_payloads(schema, None)]
        local_modes = [
            name
            for name, _ in structured_output_payloads(
                schema,
                None,
                prefer_json_object=True,
            )
        ]

        self.assertEqual(default_modes[:2], ["json_schema", "json_object"])
        self.assertEqual(local_modes[:2], ["json_object", "json_schema"])

    def test_local_judge_routes_api_extraction_failure_through_parser_repair_and_validation(self):
        scores_a = {category: 8 for category in CATEGORY_WEIGHTS}
        scores_b = {category: 7 for category in CATEGORY_WEIGHTS}
        raw = json.dumps(result_with(scores_a, scores_b))
        raw = raw.replace(
            "Response A and Response B are both marked numerically.",
            'Response A handles the "how much" framing directly.',
        )
        endpoint = JudgeEndpointConfig(
            name="Local",
            base_url="http://127.0.0.1:5000/v1",
            api_key="local-key",
            model="local-model",
            local_endpoint_mode="shared_hwui",
        )
        config = AppConfig(
            judge=JudgeConfig(
                name=endpoint.name,
                base_url=endpoint.base_url,
                api_key=endpoint.api_key,
                model=endpoint.model,
                local_endpoint_mode=endpoint.local_endpoint_mode,
            )
        )

        with patch("llmbench.judge.chat_completion") as mocked_chat, patch(
            "llmbench.judge.log_judge_pipeline_debug"
        ) as mocked_debug:
            mocked_chat.return_value = ChatCompletionResult(
                text=raw,
                response_format_mode="json_object",
                api_json_extraction_failed=True,
                api_json_parse_error="JSONDecodeError: Expecting ',' delimiter",
            )

            parsed = judge_comparison(
                config=config,
                rubric="Rubric",
                judging_profile="Profile",
                conversation_context="",
                current_prompt="Prompt",
                response_a="A",
                response_b="B",
                model_name_a="A",
                model_name_b="B",
                model="local-model",
                temperature=0.0,
                endpoint=endpoint,
                prompt_id="prompt_04",
            )

        self.assertEqual(parsed["winner"]["response"], "A")
        mocked_chat.assert_called_once()
        self.assertTrue(mocked_chat.call_args.kwargs["prefer_json_object"])
        self.assertTrue(mocked_chat.call_args.kwargs["allow_raw_on_json_parse_failure"])
        acceptance_logs = [
            call.args[1]
            for call in mocked_debug.call_args_list
            if call.args[0] == "JUDGE RESULT ACCEPTANCE"
        ]
        self.assertTrue(acceptance_logs)
        self.assertEqual(acceptance_logs[-1]["response_format_mode"], "json_object")
        self.assertTrue(acceptance_logs[-1]["api_json_extraction_failed"])
        self.assertTrue(acceptance_logs[-1]["parser_repair_recovered_object"])
        self.assertTrue(acceptance_logs[-1]["validation_passed"])


class ExtraScoreCategoryTests(unittest.TestCase):
    def test_scoring_categories_rejects_unknown_category(self):
        with self.assertRaises(JudgeError) as raised:
            scoring_categories(["Banter"])
        self.assertIn("Unknown optional score category: Banter", str(raised.exception))

    def test_base_constants_are_unchanged_without_extras(self):
        self.assertEqual(judge_output_schema(), JUDGE_OUTPUT_SCHEMA)
        self.assertEqual(output_instructions(), OUTPUT_INSTRUCTIONS)
        self.assertEqual(list(scoring_categories()), list(CATEGORY_WEIGHTS))

    def test_extended_schema_grammar_and_instructions_include_extra_categories(self):
        weights = scoring_categories(["Creativity", "Philosophical Depth"])
        schema = judge_output_schema(weights)
        scores_schema = schema["$defs"]["response"]["properties"]["scores"]
        self.assertIn("Creativity", scores_schema["required"])
        self.assertIn("Philosophical Depth", scores_schema["properties"])
        deductions_schema = schema["$defs"]["response"]["properties"]["deductions"]
        self.assertIn("Philosophical Depth", deductions_schema["required"])
        grammar = judge_output_grammar(weights)
        self.assertIn('"\\"Creativity\\"" ws ":" ws number', grammar)
        self.assertIn('"\\"Philosophical Depth\\"" ws ":" ws string', grammar)
        instructions = output_instructions(weights)
        self.assertIn('"Creativity": 0.0', instructions)
        self.assertIn('"Philosophical Depth": "..."', instructions)
        base_schema = judge_output_schema()
        self.assertNotIn("Creativity", base_schema["$defs"]["response"]["properties"]["scores"]["required"])

    def test_validate_result_requires_and_averages_extra_categories(self):
        extra = ["Moral Reasoning"]
        categories = list(scoring_categories(extra))
        scores_a = {category: 8.0 for category in categories}
        scores_b = {category: 9.0 for category in categories}
        scores_a["Moral Reasoning"] = 1.0

        result = validate_result(result_with(scores_a, scores_b, categories), extra)

        self.assertEqual(result["responses"]["A"]["overall"], 7.0)
        self.assertEqual(result["responses"]["B"]["overall"], 9.0)
        self.assertIn("Moral Reasoning", result["responses"]["A"]["deductions"])

    def test_validate_result_rejects_missing_extra_category_score(self):
        extra = ["Creativity"]
        categories = list(scoring_categories(extra))
        scores_a = {category: 8.0 for category in CATEGORY_WEIGHTS}
        scores_b = {category: 9.0 for category in categories}

        with self.assertRaises(JudgeError) as raised:
            validate_result(result_with(scores_a, scores_b, categories), extra)

        self.assertIn("response A Creativity score", str(raised.exception))

    def test_validate_result_without_extras_ignores_optional_categories(self):
        scores_a = {category: 8.0 for category in CATEGORY_WEIGHTS}
        scores_b = {category: 9.0 for category in CATEGORY_WEIGHTS}

        result = validate_result(result_with(scores_a, scores_b))

        for category in OPTIONAL_CATEGORY_WEIGHTS:
            self.assertNotIn(category, result["responses"]["A"]["scores"])


if __name__ == "__main__":
    unittest.main()
