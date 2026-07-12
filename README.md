# Helcyon-Bench

Helcyon-Bench is a small Windows-friendly Streamlit app for interactively comparing two companion models across five visible prompts.

It is not an automated benchmark. The workflow is:

1. Optionally label Response A and Response B with model names.
2. Select a prompt pack from `prompt_packs` and load it, or type your own five prompts.
3. Paste Response A and Response B for each prompt.
4. Optionally save the visible prompts back to the selected prompt pack.
5. Click Judge.
6. Read the per-prompt results and averaged category scores.

## Setup

On Windows, double-click `Setup.bat`. It creates `.venv`, installs the dependencies, and creates `config.yaml` from `config.example.yaml` if needed.

For manual setup, install the minimal dependencies:

```powershell
pip install -r requirements.txt
```

Copy the example config:

```powershell
copy config.example.yaml config.yaml
```

Edit `config.yaml` with your OpenAI-compatible judge endpoints:

```yaml
judge:
  default_endpoint: "Local"
  endpoints:
    Local:
      base_url: "http://127.0.0.1:5000/v1"
      api_key: "local-key"
      model: "local-model"
      local_endpoint_mode: "shared_hwui"
      models:
        - "local-model"
      temperature: 0.0
      max_tokens: 4800

    Local Dedicated:
      base_url: "http://127.0.0.1:5001/v1"
      api_key: "local-key"
      model: "local-model"
      local_endpoint_mode: "external_dedicated"
      models:
        - "local-model"
      temperature: 0.0
      max_tokens: 4800

    OpenAI:
      base_url: "https://api.openai.com/v1"
      api_key: "sk-your-key-here"
      model: "gpt-4o"
      models:
        - "gpt-4o"
        - "gpt-5.5"
      temperature: 1.0
      max_tokens: 4800
```

OpenAI, OpenRouter, llama.cpp, and similar compatible `/chat/completions` endpoints are supported.
For the normal local workflow, choose `Local` to use HWUI's shared llama.cpp server on `5000` and the currently loaded HWUI model. Helcyon-Bench marks shared requests with `X-HelcyonBench-Run: true`; HWUI should preserve the llama-server while such a request or configured bench lock is active. `Local Dedicated` on `5001` is optional for machines with enough VRAM or a separate judge host.
When the local OpenAI-compatible judge server is running, click `Refresh Judge Models` to populate the Judge dropdown from `/v1/models`.
Use `Test Judge Connection` before a benchmark run to confirm Helcyon-Bench can reach `/v1/models` and complete a tiny structured `/v1/chat/completions` request with the selected judge model.
Before benchmark judging starts, Helcyon-Bench checks `/v1/models` and runs a tiny structured `/v1/chat/completions` smoke test.
Judge requests use structured output controls where available: JSON schema first, JSON object mode next, and llama.cpp grammar as the local fallback.

## Run

Double-click `Run.bat`, or run:

```powershell
streamlit run app.py
```

## Notes

- The app expects judge output as structured JSON.
- Judge debug logs are written to `judge_logs/*.jsonl` by default. Set `judge.debug_logging: false` in `config.yaml` to disable them.
- Reports can be exported as Markdown.
- The sidebar keeps a lightweight in-session history of recent winners.
- The app does not load or switch models. Generate responses elsewhere, then paste them in for comparison.
- Prompt packs are JSON files in `prompt_packs` and only require `title` and `prompt` entries.
- Packs may set an optional `"rubric"` field (e.g. `"companion"`) to pick the scoring rubric explicitly. When absent, Creativity packs use `creativity.md`, Philosophy packs `philosophy.md`, Morals packs `morals.md`, Uncensored packs `uncensored.md`, Humour packs `humour.md`, and everything else (including Companion) uses `companion.md`. Empathy/distress-signalling packs also get `distress_calibration.md` appended after the primary rubric.

