from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from llmbench.api import ApiError, ChatCompletionResult, chat_completion, debug_logging_enabled
from llmbench.config import AppConfig, JudgeEndpointConfig


class JudgeError(Exception):
    """Raised when judging fails or the judge output is invalid."""

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


JUDGE_LOG_PATH = Path(__file__).resolve().parent.parent / "judge_logs" / "judge_io.jsonl"
JUDGE_PIPELINE_DEBUG_PATH = Path(__file__).resolve().parent.parent / "judge_logs" / "judge_pipeline_debug.jsonl"


CATEGORY_WEIGHTS = {
    "Emotional Presence": 1.0,
    "Conversation Flow": 1.0,
    "Evidence Discipline": 1.0,
    "User Frame Following": 1.0,
    "Humour": 1.0,
    "Restraint": 1.0,
}

OPTIONAL_CATEGORY_WEIGHTS = {
    "Creativity": 1.0,
    "Philosophical Depth": 1.0,
    "Moral Reasoning": 1.0,
}


def scoring_categories(extra_categories: list[str] | None = None) -> dict[str, float]:
    weights = dict(CATEGORY_WEIGHTS)
    for category in extra_categories or []:
        if category not in OPTIONAL_CATEGORY_WEIGHTS:
            raise JudgeError(
                f"Unknown optional score category: {category}. "
                f"Known optional categories: {', '.join(OPTIONAL_CATEGORY_WEIGHTS)}."
            )
        weights[category] = OPTIONAL_CATEGORY_WEIGHTS[category]
    return weights


def category_properties(value_schema: dict[str, Any], categories: list[str] | None = None) -> dict[str, Any]:
    return {category: value_schema for category in (categories or list(CATEGORY_WEIGHTS))}


JUDGE_STRING_DESCRIPTION = (
    "Use one complete sentence or phrase. Do not use quotation marks inside JSON string values; "
    "paraphrase referenced words or phrases instead of quoting them."
)


def judge_output_schema(weights: dict[str, float] | None = None) -> dict[str, Any]:
    categories = list(weights or CATEGORY_WEIGHTS)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["responses", "comparison", "final_verdict"],
        "properties": {
            "responses": {
                "type": "object",
                "additionalProperties": False,
                "required": ["A", "B"],
                "properties": {
                    "A": {"$ref": "#/$defs/response"},
                    "B": {"$ref": "#/$defs/response"},
                },
            },
            "comparison": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "more_natural",
                    "better_frame_following",
                    "stronger_emotional_presence",
                    "better_evidence_discipline",
                    "better_conclusion",
                    "more_enjoyable",
                    "weaknesses",
                ],
                "properties": {
                    "more_natural": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "better_frame_following": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "stronger_emotional_presence": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "better_evidence_discipline": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "better_conclusion": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "more_enjoyable": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                    "weaknesses": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                },
            },
            "final_verdict": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
        },
        "$defs": {
            "response": {
                "type": "object",
                "additionalProperties": False,
                "required": ["scores", "strengths", "deductions", "weaknesses"],
                "properties": {
                    "scores": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": categories,
                        "properties": category_properties(
                            {"type": "number", "minimum": 0, "maximum": 10}, categories
                        ),
                    },
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                        "description": "Each array entry must be a complete sentence or phrase.",
                    },
                    "deductions": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": categories,
                        "properties": category_properties(
                            {"type": "string", "description": JUDGE_STRING_DESCRIPTION}, categories
                        ),
                    },
                    "weaknesses": {
                        "type": "array",
                        "items": {"type": "string", "description": JUDGE_STRING_DESCRIPTION},
                        "description": "Each array entry must be a complete sentence or phrase.",
                    },
                },
            }
        },
    }


JUDGE_OUTPUT_SCHEMA: dict[str, Any] = judge_output_schema()


def grammar_category_object_rule(rule_name: str, categories: list[str], value_rule: str) -> str:
    lines = [f'{rule_name} ::= "{{" ws']
    for index, category in enumerate(categories):
        escaped = category.replace('"', '\\"')
        suffix = ' ws "," ws' if index + 1 < len(categories) else ""
        lines.append(f'  "\\"{escaped}\\"" ws ":" ws {value_rule}{suffix}')
    lines.append('ws "}"')
    return "\n".join(lines)


def judge_output_grammar(weights: dict[str, float] | None = None) -> str:
    categories = list(weights or CATEGORY_WEIGHTS)
    scores_rule = grammar_category_object_rule("scores", categories, "number")
    deductions_rule = grammar_category_object_rule("deductions", categories, "string")
    return rf'''
root ::= ws "{{" ws responses-pair ws "," ws comparison-pair ws "," ws final-verdict-pair ws "}}" ws

responses-pair ::= "\"responses\"" ws ":" ws "{{" ws "\"A\"" ws ":" ws response ws "," ws "\"B\"" ws ":" ws response ws "}}"
response ::= "{{" ws scores-pair ws "," ws strengths-pair ws "," ws deductions-pair ws "," ws weaknesses-pair ws "}}"

scores-pair ::= "\"scores\"" ws ":" ws scores
{scores_rule}

deductions-pair ::= "\"deductions\"" ws ":" ws deductions
{deductions_rule}

strengths-pair ::= "\"strengths\"" ws ":" ws string-array
weaknesses-pair ::= "\"weaknesses\"" ws ":" ws string-array

comparison-pair ::= "\"comparison\"" ws ":" ws comparison
comparison ::= "{{" ws
  "\"more_natural\"" ws ":" ws string ws "," ws
  "\"better_frame_following\"" ws ":" ws string ws "," ws
  "\"stronger_emotional_presence\"" ws ":" ws string ws "," ws
  "\"better_evidence_discipline\"" ws ":" ws string ws "," ws
  "\"better_conclusion\"" ws ":" ws string ws "," ws
  "\"more_enjoyable\"" ws ":" ws string ws "," ws
  "\"weaknesses\"" ws ":" ws string
ws "}}"

final-verdict-pair ::= "\"final_verdict\"" ws ":" ws string

string-array ::= "[" ws (string (ws "," ws string)*)? ws "]"
string ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" hex hex hex hex))* "\""
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)?
hex ::= [0-9a-fA-F]
ws ::= [ \t\n\r]*
'''.strip()


JUDGE_OUTPUT_GRAMMAR = judge_output_grammar()


SYSTEM_PROMPT = """You are Helcyon-Bench, a careful evaluator of model responses.
Compare two submitted responses against the conversation context, current prompt, and rubric.
Use the supplied judging profile as the benchmark philosophy for this prompt pack.
Behave like an experienced examiner marking against a published marking scheme.
Mark Response A fully before marking Response B. Only compare them after both are marked.
Return valid JSON only. Do not include markdown, comments, or prose outside JSON."""


def response_example_block(categories: list[str]) -> str:
    scores_lines = ",\n".join(f'        "{category}": 0.0' for category in categories)
    deduction_lines = ",\n".join(f'        "{category}": "..."' for category in categories)
    return (
        "{\n"
        '      "scores": {\n'
        f"{scores_lines}\n"
        "      },\n"
        '      "strengths": ["..."],\n'
        '      "deductions": {\n'
        f"{deduction_lines}\n"
        "      },\n"
        '      "weaknesses": ["..."]\n'
        "    }"
    )


def output_instructions(weights: dict[str, float] | None = None) -> str:
    categories = list(weights or CATEGORY_WEIGHTS)
    example = response_example_block(categories)
    return f"""Return this JSON shape:
{{
  "responses": {{
    "A": {example},
    "B": {example}
  }},
  "comparison": {{
    "more_natural": "...",
    "better_frame_following": "...",
    "stronger_emotional_presence": "...",
    "better_evidence_discipline": "...",
    "better_conclusion": "...",
    "more_enjoyable": "...",
    "weaknesses": "..."
  }},
  "final_verdict": "..."
}}

JSON string rules:
- Do not use quotation marks inside JSON string values.
- When referring to words or phrases from a response, paraphrase them instead of quoting them.
- Deduction strings must never quote words or phrases from the user's prompt.
- Deduction strings must paraphrase the user's prompt naturally instead of copying its wording.
- Do not use quotation marks inside deduction strings.
- If a deduction refers to the prompt, use descriptions such as the user's question, the prompt, the scenario, or the request instead of quoting words from it.
- Keep every string value as one complete sentence or phrase.
- Do not split a sentence fragment across multiple array entries.

Scoring method:
1. Mark Response A independently against the rubric.
2. Award every category score for Response A.
3. Explain deductions from full marks for every Response A category. If no meaningful deduction exists, say "No meaningful deduction."
4. Repeat the same process independently for Response B.
5. Do not provide an overall score, winner, or confidence. The application calculates those from the category scores.
6. Only after both responses are marked, compare them by referring to category evidence.
7. Write final_verdict last. If final_verdict names Response A or Response B as the winner, that written winner must agree with the category scores you awarded.

Never return N/A. Every category score must be a number from 0 to 10.
Do not use strings for scores. Do not omit categories.
If a category is less directly relevant to the prompt, still score how well the response handled that dimension in context.
For example, if humour is not relevant, score whether the response appropriately avoided forced humour.

Scores must be earned, not guessed. Every deduction from 10.0 must correspond to an identifiable weakness.
Avoid score inflation and score compression.
Use this scale:
- 10.0: Essentially impossible to improve in any meaningful conversational way. Extremely rare.
- 9.5: Outstanding. Only tiny refinements possible.
- 9.0: Excellent. Clearly strong for the active judging profile. Small weaknesses exist.
- 8.0: Very good. Noticeable room for improvement.
- 7.0: Good. Several conversational weaknesses.
- 6.0: Competent but average.
- 5.0 and below: Increasingly poor fit for the active judging profile.

Comparison language must be examiner-like. Avoid subjective phrasing such as "I preferred".
Instead write things like "Response B achieved a higher Conversation Flow score because..."."""


OUTPUT_INSTRUCTIONS = output_instructions()


def log_judge_event(event: str, payload: dict[str, Any]) -> None:
    if not debug_logging_enabled():
        return
    try:
        JUDGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            **payload,
        }
        with JUDGE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_judge_pipeline_debug(stage: str, payload: dict[str, Any]) -> None:
    if not debug_logging_enabled():
        return
    try:
        JUDGE_PIPELINE_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "temporary_debug": True,
            "stage": stage,
            **payload,
        }
        with JUDGE_PIPELINE_DEBUG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def build_messages(
    rubric: str,
    judging_profile: str,
    conversation_context: str,
    current_prompt: str,
    response_a: str,
    response_b: str,
    model_name_a: str,
    model_name_b: str,
    extra_categories: list[str] | None = None,
) -> list[dict[str, str]]:
    instructions = output_instructions(scoring_categories(extra_categories))
    content = f"""Judging profile:
{judging_profile or "Use the rubric's default judging philosophy."}

Use this judging profile as the primary evaluation philosophy for the selected prompt pack.
Keep the rubric's scoring categories and JSON schema stable, but if the rubric's philosophy conflicts with the judging profile, prefer the judging profile.

Rubric:
{rubric}

{instructions}

Conversation context, if any:
<<<CONTEXT
{conversation_context or "No prior context provided."}
CONTEXT

Current prompt:
<<<PROMPT
{current_prompt}
PROMPT

Response A model name:
{model_name_a or "Response A"}

Response A:
<<<RESPONSE_A
{response_a}
RESPONSE_A

Response B model name:
{model_name_b or "Response B"}

Response B:
<<<RESPONSE_B
{response_b}
RESPONSE_B"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def strip_markdown_fences(text: str) -> str:
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    return cleaned.strip()


def strip_local_judge_wrappers(text: str) -> str:
    cleaned = re.sub(r"(?m)^\[(?:json_schema|json_object|none|grammar)\]\s*", "", str(text or ""))
    cleaned = cleaned.replace("<|im_end|>", "")
    return cleaned.strip()


def first_complete_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
            if depth < 0:
                return None
    return None


def broad_json_object_slice(text: str) -> str | None:
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        return None
    return text[first : last + 1]


def log_parse_failure(stage: str, raw_content: str, exc: BaseException) -> None:
    log_judge_event(
        "judge_json_parse_failed",
        {
            "stage": stage,
            "raw_assistant_content": raw_content,
            "raw_content_received": bool(raw_content),
            "json_parse_exception": f"{exc.__class__.__name__}: {exc}",
            "raw_content_preview": raw_content[:500],
        },
    )


def excerpt_around(text: str, position: int | None, radius: int = 180) -> str:
    if position is None:
        return str(text or "")[: radius * 2]
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end]


def json_error_position(exc: BaseException) -> int | None:
    return exc.pos if isinstance(exc, json.JSONDecodeError) else None


def log_repair_parse_event(
    stage: str,
    raw_content: str,
    *,
    parse_error: BaseException | None = None,
    original_text: str = "",
    repaired_text: str = "",
) -> None:
    position = json_error_position(parse_error) if parse_error else None
    log_judge_event(
        "judge_json_repair_parse",
        {
            "stage": stage,
            "raw_assistant_content": raw_content,
            "raw_content_received": bool(raw_content),
            "parse_error": (
                f"{parse_error.__class__.__name__}: {parse_error}" if parse_error else ""
            ),
            "embedded_quote_recovery_attempted": True,
            "error_position": position,
            "original_error_excerpt": excerpt_around(original_text or raw_content, position),
            "repaired_error_excerpt": excerpt_around(repaired_text, position) if repaired_text else "",
            "raw_content_preview": raw_content[:500],
        },
    )


def repair_unescaped_quotes_in_json_strings(text: str) -> str:
    repaired = []
    in_string = False
    escaped = False
    length = len(text)
    terminators = {",", "}", "]", ":"}

    for index, char in enumerate(text):
        if not in_string:
            repaired.append(char)
            if char == '"':
                in_string = True
                escaped = False
            continue

        if escaped:
            repaired.append(char)
            escaped = False
            continue

        if char == "\\":
            repaired.append(char)
            escaped = True
            continue

        if char == '"':
            next_index = index + 1
            while next_index < length and text[next_index].isspace():
                next_index += 1
            if next_index >= length or text[next_index] in terminators:
                repaired.append(char)
                in_string = False
            else:
                repaired.append('\\"')
            continue

        repaired.append(char)

    return "".join(repaired)


def parse_json(
    text: str,
    debug_context: dict[str, Any] | None = None,
    repair_status: dict[str, bool] | None = None,
) -> dict[str, Any]:
    debug_context = debug_context or {}
    if repair_status is not None:
        repair_status["parser_repair_attempted"] = False
        repair_status["parser_repair_recovered_object"] = False
    current_json_text = text
    repair_stage_logged = False
    try:
        data = json.loads(text)
        log_judge_pipeline_debug(
            "AFTER JUDGE JSON EXTRACTION",
            {
                **debug_context,
                "extraction_path": "raw_json_load",
                "text": text,
                "changed_from_input": False,
            },
        )
    except json.JSONDecodeError as original_exc:
        log_parse_failure("raw", text, original_exc)
        cleaned = strip_local_judge_wrappers(strip_markdown_fences(text))
        try:
            data = json.loads(cleaned)
            current_json_text = cleaned
            log_judge_pipeline_debug(
                "AFTER JUDGE JSON EXTRACTION",
                {
                    **debug_context,
                    "extraction_path": "stripped_wrappers",
                    "text": cleaned,
                    "changed_from_input": cleaned != text,
                },
            )
        except json.JSONDecodeError as cleaned_exc:
            log_parse_failure("stripped_markdown_fences", text, cleaned_exc)
            extracted = first_complete_json_object(cleaned)
            if not extracted:
                extracted = broad_json_object_slice(cleaned)
            if not extracted:
                raise JudgeError(
                    "The judge did not return JSON. "
                    f"json_parse_exception={cleaned_exc.__class__.__name__}: {cleaned_exc}; "
                    f"raw_content_received={bool(text)}; first_500={text[:500]}",
                    raw_response=text,
                ) from original_exc
            log_judge_pipeline_debug(
                "AFTER JUDGE JSON EXTRACTION",
                {
                    **debug_context,
                    "extraction_path": "first_complete_or_broad_object",
                    "text": extracted,
                    "changed_from_input": extracted != text,
                },
            )
            current_json_text = extracted
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError as exc:
                log_parse_failure("extracted_first_brace_to_last_brace", text, exc)
                log_repair_parse_event(
                    "normal_parse_failed_repair_attempted",
                    text,
                    parse_error=exc,
                    original_text=extracted,
                )
                if repair_status is not None:
                    repair_status["parser_repair_attempted"] = True
                repaired = repair_unescaped_quotes_in_json_strings(extracted)
                current_json_text = repaired
                repair_stage_logged = True
                log_judge_pipeline_debug(
                    "AFTER JSON REPAIR",
                    {
                        **debug_context,
                        "text": repaired,
                        "changed_from_extracted": repaired != extracted,
                        "parse_error": f"{exc.__class__.__name__}: {exc}",
                    },
                )
                try:
                    data = json.loads(repaired)
                except json.JSONDecodeError as repair_exc:
                    log_repair_parse_event(
                        "repair_parse_failed",
                        text,
                        parse_error=repair_exc,
                        original_text=extracted,
                        repaired_text=repaired,
                    )
                    raise JudgeError(
                        "The judge returned malformed JSON after robust extraction. "
                        f"json_parse_exception={repair_exc.__class__.__name__}: {repair_exc}; "
                        f"raw_content_received={bool(text)}; first_500={text[:500]}",
                        raw_response=text,
                    ) from repair_exc
                log_repair_parse_event(
                    "repair_parse_succeeded",
                    text,
                    parse_error=exc,
                    original_text=extracted,
                    repaired_text=repaired,
                )
                if repair_status is not None:
                    repair_status["parser_repair_recovered_object"] = True

    if not isinstance(data, dict):
        raise JudgeError("The judge JSON must be an object.")
    if not repair_stage_logged:
        log_judge_pipeline_debug(
            "AFTER JSON REPAIR",
            {
                **debug_context,
                "text": current_json_text,
                "repair_attempted": False,
                "changed_from_extracted": False,
            },
        )
    log_judge_pipeline_debug(
        "PARSED OBJECT",
        {
            **debug_context,
            "object": data,
            "object_json": json.dumps(data, ensure_ascii=False, sort_keys=True),
        },
    )
    return data


def is_local_judge_endpoint(endpoint: JudgeEndpointConfig) -> bool:
    mode = str(getattr(endpoint, "local_endpoint_mode", "") or "").lower()
    if mode in {"shared_hwui", "external_dedicated"}:
        return True
    base_url = str(getattr(endpoint, "base_url", "") or "").lower()
    return "://127.0.0.1" in base_url or "://localhost" in base_url


_VERDICT_ADVERBS = r"(?:narrowly|just|barely|slightly|marginally|clearly|comfortably|decisively|definitely|ultimately|overall|somewhat|much|far|easily)"


def _verdict_patterns_for(letter: str) -> list[str]:
    return [
        rf"\bresponse\s+{letter}\s+(?:(?:{_VERDICT_ADVERBS})\s+)?(?:wins?|edges?(?:\s+it)?|takes(?:\s+it)?|prevails|comes\s+out\s+ahead|has\s+the\s+edge)\b",
        rf"\b{letter}\s+(?:(?:{_VERDICT_ADVERBS})\s+)?(?:wins?|edges?(?:\s+it)?|takes(?:\s+it)?|prevails|comes\s+out\s+ahead|has\s+the\s+edge)\b",
        rf"\b(?:response\s+)?{letter}\s+is\s+the\s+winner\b",
        rf"\b(?:winner|winning\s+response)\s*(?:is|:|-)?\s*(?:response\s+)?{letter}\b",
        # "A is [narrowly] the stronger response" / "B is clearly the better answer"
        rf"\b(?:response\s+)?{letter}\s+is\s+(?:(?:{_VERDICT_ADVERBS})\s+)?(?:the\s+)?(?:stronger|better|superior|preferred|winning)\s+(?:response|answer|choice|option|one|overall)?\b",
        # "A is the stronger of the two"
        rf"\b(?:response\s+)?{letter}\s+is\s+(?:(?:{_VERDICT_ADVERBS})\s+)?(?:the\s+)?(?:stronger|better|superior|preferred)\s+of\s+the\s+two\b",
    ]


def verdict_response(final_verdict: str) -> str | None:
    text = str(final_verdict or "")
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return None

    # Bare "Response A" / "Response B" (optionally with trailing punctuation) as the
    # entire verdict text unambiguously names the winner even without a verb.
    bare = normalized.rstrip(" .!—-").strip().lower()
    if bare in {"response a", "a"}:
        return "A"
    if bare in {"response b", "b"}:
        return "B"

    patterns = {"A": _verdict_patterns_for("a"), "B": _verdict_patterns_for("b")}
    matches = {
        response
        for response, response_patterns in patterns.items()
        if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in response_patterns)
    }
    if len(matches) == 1:
        return next(iter(matches))
    return None


def enforce_verdict_consistency(data: dict[str, Any]) -> dict[str, Any]:
    verdict_winner = verdict_response(str(data.get("final_verdict", "")))
    calculated_winner = str(data.get("winner", {}).get("response", "")).upper()
    if verdict_winner is None:
        data["verdict_consistency"] = {
            "status": "not_checked",
            "reason": "final_verdict did not clearly name Response A or Response B as the winner",
        }
        return data

    if calculated_winner == verdict_winner:
        data["verdict_consistency"] = {
            "status": "ok",
            "verdict_response": verdict_winner,
            "calculated_response": calculated_winner,
        }
        return data

    warning = (
        "final_verdict named Response "
        f"{verdict_winner}, but score-derived winner.response was {calculated_winner or 'unknown'}. "
        "Repaired winner.response from the written verdict without changing scores."
    )
    data.setdefault("winner", {})["response"] = verdict_winner
    data["verdict_consistency"] = {
        "status": "repaired",
        "verdict_response": verdict_winner,
        "calculated_response": calculated_winner,
        "warning": warning,
    }
    log_judge_event(
        "verdict_consistency_repaired",
        {
            "warning": warning,
            "final_verdict": data.get("final_verdict", ""),
            "winner": data.get("winner", {}),
            "response_a_overall": data.get("responses", {}).get("A", {}).get("overall"),
            "response_b_overall": data.get("responses", {}).get("B", {}).get("overall"),
        },
    )
    return data


def validate_result(data: dict[str, Any], extra_categories: list[str] | None = None) -> dict[str, Any]:
    if "responses" not in data or not isinstance(data["responses"], dict):
        raise JudgeError("The judge JSON is missing responses.")

    weights = scoring_categories(extra_categories)
    data["responses"] = {
        key: validate_response_result(data["responses"].get(key), key, weights) for key in ["A", "B"]
    }
    data["winner"] = calculate_winner(data["responses"])

    comparison = data.get("comparison", {})
    if not isinstance(comparison, dict):
        comparison = {}
    data["comparison"] = {
        "more_natural": str(comparison.get("more_natural", "")),
        "better_frame_following": str(comparison.get("better_frame_following", "")),
        "stronger_emotional_presence": str(comparison.get("stronger_emotional_presence", "")),
        "better_evidence_discipline": str(comparison.get("better_evidence_discipline", "")),
        "better_conclusion": str(comparison.get("better_conclusion", "")),
        "more_enjoyable": str(comparison.get("more_enjoyable", "")),
        "weaknesses": str(comparison.get("weaknesses", "")),
    }

    data["final_verdict"] = str(data.get("final_verdict", ""))
    return enforce_verdict_consistency(data)


def validate_response_result(value: Any, label: str, weights: dict[str, float] | None = None) -> dict[str, Any]:
    weights = weights or CATEGORY_WEIGHTS
    if not isinstance(value, dict):
        raise JudgeError(f"The judge JSON is missing response {label}.")
    if "scores" not in value or not isinstance(value["scores"], dict):
        raise JudgeError(f"The judge JSON is missing response {label} scores.")

    value["scores"] = normalize_scores(value["scores"], label, weights)
    value["overall"] = calculate_overall(value["scores"], weights)

    for key in ["strengths", "weaknesses"]:
        items = value.get(key, [])
        if isinstance(items, str):
            items = [items]
        if not isinstance(items, list):
            items = []
        value[key] = [str(item) for item in items]

    deductions = value.get("deductions")
    if not isinstance(deductions, dict):
        raise JudgeError(f"The judge JSON is missing response {label} deductions.")
    missing_deductions = [category for category in weights if category not in deductions]
    if missing_deductions:
        missing = ", ".join(missing_deductions)
        raise JudgeError(f"The judge JSON is missing response {label} deduction notes for {missing}.")
    value["deductions"] = {
        category: str(deductions.get(category, "")) for category in weights
    }
    return value


def normalize_scores(scores: dict[str, Any], label: str, weights: dict[str, float] | None = None) -> dict[str, float]:
    normalized = {}
    for category in weights or CATEGORY_WEIGHTS:
        if category not in scores:
            raise JudgeError(f"The judge JSON is missing response {label} {category} score.")
        normalized[category] = clamp_score(scores[category], response_label=label, category=category)
    return normalized


def calculate_overall(scores: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or CATEGORY_WEIGHTS
    total_weight = sum(weights.values())
    weighted_total = sum(scores[category] * weight for category, weight in weights.items())
    return round(weighted_total / total_weight, 2)


def calculate_winner(responses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    score_a = float(responses["A"]["overall"])
    score_b = float(responses["B"]["overall"])
    difference = round(score_b - score_a, 2)
    if abs(difference) < 0.01:
        winner = "TIE"
    elif difference > 0:
        winner = "B"
    else:
        winner = "A"
    return {
        "response": winner,
        "model_name": "",
        "confidence": calculate_confidence(abs(difference)),
        "score_difference": abs(difference),
    }


def calculate_confidence(score_gap: float) -> int:
    if score_gap < 0.01:
        return 50
    return min(99, int(round(55 + (score_gap * 12))))


def clamp_score(
    value: Any,
    maximum: float = 10.0,
    response_label: str | None = None,
    category: str | None = None,
) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        location = ""
        if response_label and category:
            location = f" for response {response_label} {category}"
        raise JudgeError(
            f"Invalid score value{location}: {value!r}. Scores must be numeric values from 0 to 10; never return N/A or strings."
        )
    return max(0.0, min(maximum, score))


def judge_comparison(
    *,
    config: AppConfig,
    rubric: str,
    judging_profile: str,
    conversation_context: str,
    current_prompt: str,
    response_a: str,
    response_b: str,
    model_name_a: str,
    model_name_b: str,
    model: str,
    temperature: float,
    endpoint: JudgeEndpointConfig | None = None,
    extra_headers: dict[str, str] | None = None,
    prompt_id: str = "",
    extra_score_categories: list[str] | None = None,
) -> dict[str, Any]:
    weights = scoring_categories(extra_score_categories)
    messages = build_messages(
        rubric,
        judging_profile,
        conversation_context,
        current_prompt,
        response_a,
        response_b,
        model_name_a,
        model_name_b,
        extra_categories=extra_score_categories,
    )
    judge_endpoint = endpoint or config.judge
    prefer_json_object = is_local_judge_endpoint(judge_endpoint)
    debug_context = {
        "prompt_id": prompt_id,
        "judge_model": model,
        "endpoint": judge_endpoint.name,
    }
    log_judge_pipeline_debug(
        "PROMPT CONSTRUCTION",
        {
            **debug_context,
            "messages": messages,
            "messages_json": json.dumps(messages, ensure_ascii=False),
        },
    )
    try:
        completion = chat_completion(
            base_url=judge_endpoint.base_url,
            api_key=judge_endpoint.api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=judge_endpoint.max_tokens,
            max_completion_tokens=judge_endpoint.max_completion_tokens,
            json_schema=judge_output_schema(weights),
            grammar=judge_output_grammar(weights),
            extra_headers=extra_headers,
            endpoint_name=judge_endpoint.name,
            prompt_id=prompt_id,
            prefer_json_object=prefer_json_object,
            allow_raw_on_json_parse_failure=prefer_json_object,
            return_metadata=True,
        )
    except ApiError as exc:
        raise JudgeError(str(exc), raw_response=getattr(exc, "raw_response", None)) from exc
    completion_result = (
        completion
        if isinstance(completion, ChatCompletionResult)
        else ChatCompletionResult(text=str(completion), response_format_mode="")
    )
    raw = completion_result.text
    debug_context = {
        **debug_context,
        "response_format_mode": completion_result.response_format_mode,
        "api_json_extraction_failed": completion_result.api_json_extraction_failed,
    }
    log_judge_event(
        "raw_judge_output",
        {
            "model": model,
            "endpoint": judge_endpoint.name,
            "response_format_mode": completion_result.response_format_mode,
            "api_json_extraction_failed": completion_result.api_json_extraction_failed,
            "api_json_parse_error": completion_result.api_json_parse_error,
            "raw_output": raw,
        },
    )
    try:
        log_judge_pipeline_debug(
            "RAW TEXT ENTERING JUDGE PARSER",
            {
                **debug_context,
                "text": raw,
            },
        )
        repair_status: dict[str, bool] = {}
        parsed_object = parse_json(raw, debug_context=debug_context, repair_status=repair_status)
        log_judge_pipeline_debug(
            "PARSED OBJECT BEFORE VALIDATION",
            {
                **debug_context,
                "object": parsed_object,
                "object_json": json.dumps(parsed_object, ensure_ascii=False, sort_keys=True),
            },
        )
        try:
            parsed = validate_result(parsed_object, extra_score_categories)
        except JudgeError:
            log_judge_pipeline_debug(
                "JUDGE RESULT ACCEPTANCE",
                {
                    **debug_context,
                    "parser_repair_recovered_object": repair_status.get("parser_repair_recovered_object", False),
                    "validation_passed": False,
                },
            )
            raise
        log_judge_pipeline_debug(
            "JUDGE RESULT ACCEPTANCE",
            {
                **debug_context,
                "parser_repair_recovered_object": repair_status.get("parser_repair_recovered_object", False),
                "validation_passed": True,
            },
        )
        log_judge_event(
            "parsed_judge_result",
            {
                "model": model,
                "endpoint": judge_endpoint.name,
                "response_format_mode": completion_result.response_format_mode,
                "api_json_extraction_failed": completion_result.api_json_extraction_failed,
                "parser_repair_recovered_object": repair_status.get("parser_repair_recovered_object", False),
                "validation_passed": True,
                "parsed_result": parsed,
            },
        )
        return parsed
    except JudgeError as exc:
        if getattr(exc, "raw_response", None) is None:
            exc.raw_response = raw
        raise

