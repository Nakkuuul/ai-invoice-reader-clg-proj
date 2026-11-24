# Zenith — AI Invoice & Receipt Intelligence
**Course:** SCSE4041 Prompt Engineering | **Problem Pool ID:** C11 | **Team:** Zenith

## Problem
Small businesses manually enter invoice and receipt details into accounting systems, causing extra work, delays and errors. This prototype accepts invoice/receipt images or text and uses prompt-engineered extraction (schema + few-shot + safeguards) with ChatGPT or Claude to produce structured JSON, flag uncertain fields and check calculations.

## Features
- Invoice/receipt image upload or text input, plus one-click synthetic sample invoices
- OpenAI (ChatGPT) or Anthropic (Claude) provider selection
- Four prompt versions: V1 baseline (Milestone 1) → V2 schema → V3 safeguards → V4 strict + few-shot
- JSON display and download
- Rule-based checks: required keys, line arithmetic, subtotal, subtotal + tax + charges = total, date format, GSTIN format
- Optional second-stage AI validation prompt

## Quick start (Windows)
Double-click **`run_app.bat`**. The first time, it creates `.venv`, installs the dependencies and copies `.env.example` to `.env`. Then open http://localhost:8501.

Manual alternative:
```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```
Put your API key in `.env` (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) or paste it into the sidebar.

## Offline tests (no API key needed)
```bat
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest -q tests
```

## Demonstrating prompt engineering
Load each sample in `sample_data/` and run it through V1–V4 on both providers. Save every JSON output and compare JSON validity, field coverage, uncertainty flags, fabricated values and arithmetic-mismatch detection. Record the results in `tests/test_cases.csv` and the prompt changes in `tests/prompt_iteration_log.csv`.

## Safety and limitations
Requires an API key, internet and model access; API use may incur charges. Use synthetic, public or anonymized invoices only. This is not a certified accounting or tax system, and a human must review the output before financial use.
