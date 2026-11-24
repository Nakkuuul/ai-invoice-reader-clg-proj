import base64
import json
import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from prompts import PROMPTS, VALIDATION_PROMPT
from validation import validate_invoice_json

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

st.set_page_config(page_title="Zenith | Invoice Intelligence", page_icon="🧾", layout="wide")
st.title("🧾 Zenith — AI Invoice & Receipt Intelligence")
st.caption("SCSE4041 Prompt Engineering | Problem Pool C11 | Team Zenith")
st.info("Use synthetic, public or anonymized invoices only. Human review is required before accounting use.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("AI configuration")
    provider = st.selectbox("Provider", ["OpenAI", "Anthropic"])
    if provider == "OpenAI":
        key = st.text_input("OpenAI API key", os.getenv("OPENAI_API_KEY", ""), type="password")
        model = st.text_input("Model", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    else:
        key = st.text_input("Anthropic API key", os.getenv("ANTHROPIC_API_KEY", ""), type="password")
        model = st.text_input("Model", os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"))
    version = st.selectbox("Prompt version", list(PROMPTS.keys()), index=len(PROMPTS) - 1)
    use_validator = st.checkbox("Run second-stage validation prompt", True)
    with st.expander("View selected prompt"):
        st.code(PROMPTS[version], language="text")

# ---------------- Input ----------------
SAMPLES = sorted((BASE / "sample_data").glob("*.txt"))
if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""


def load_sample():
    st.session_state.doc_text = (BASE / "sample_data" / st.session_state.sample_choice).read_text(encoding="utf-8")


c1, c2 = st.columns([3, 1])
with c1:
    st.selectbox("Synthetic test invoices", [p.name for p in SAMPLES], key="sample_choice")
with c2:
    st.write("")
    st.button("Load sample", on_click=load_sample, width="stretch")

image = st.file_uploader("Upload invoice/receipt image", type=["png", "jpg", "jpeg", "webp"])
text_input = st.text_area("Or paste invoice/receipt text", key="doc_text", height=220)
go = st.button("Extract invoice details", type="primary", width="stretch")


# ---------------- Model calls ----------------
def build_text(prompt, text, has_image):
    doc = text.strip() if text and text.strip() else ("(See the attached image.)" if has_image else "")
    return f"{prompt}\n\nDOCUMENT:\n<<<\n{doc}\n>>>"


def ask_openai(key, model, prompt, text, img, mime):
    from openai import OpenAI
    content = [{"type": "input_text", "text": build_text(prompt, text, bool(img))}]
    if img:
        content.append({"type": "input_image",
                        "image_url": f"data:{mime};base64,{base64.b64encode(img).decode()}"})
    res = OpenAI(api_key=key).responses.create(model=model, input=[{"role": "user", "content": content}])
    return res.output_text


def ask_anthropic(key, model, prompt, text, img, mime):
    import anthropic
    content = []
    if img:
        media = mime if mime in ("image/jpeg", "image/png", "image/webp", "image/gif") else "image/jpeg"
        content.append({"type": "image", "source": {"type": "base64", "media_type": media,
                                                    "data": base64.b64encode(img).decode()}})
    content.append({"type": "text", "text": build_text(prompt, text, bool(img))})
    res = anthropic.Anthropic(api_key=key).messages.create(
        model=model, max_tokens=16000, messages=[{"role": "user", "content": content}])
    if res.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    if res.stop_reason == "max_tokens":
        raise RuntimeError("Response was cut off (max_tokens reached).")
    return "\n".join(b.text for b in res.content if b.type == "text")


def ask(prompt, text, img, mime):
    fn = ask_openai if provider == "OpenAI" else ask_anthropic
    return fn(key, model, prompt, text, img, mime)


def parse_json(raw):
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group())
        raise ValueError("Model did not return valid JSON. Try another prompt version.")


# ---------------- Run ----------------
if go:
    if not key:
        st.error("Enter your provider API key in the sidebar (or put it in a .env file).")
    elif not image and not text_input.strip():
        st.warning("Upload a document image or paste/load its text.")
    else:
        img = image.getvalue() if image else None
        mime = image.type if image else None
        raw = None
        try:
            with st.spinner(f"Extracting with {version}..."):
                raw = ask(PROMPTS[version], text_input, img, mime)
                data = parse_json(raw)
            st.success(f"Extraction completed using {version} on {model}.")
            a, b = st.columns(2)
            with a:
                st.subheader("Extracted JSON")
                st.json(data)
                st.download_button("Download JSON", json.dumps(data, indent=2),
                                   file_name="zenith_extraction.json", mime="application/json")
            with b:
                st.subheader("Rule-based checks")
                for check in validate_invoice_json(data):
                    (st.success if check["status"] == "PASS" else st.warning)(
                        f"{check['status']}: {check['message']}")
            if use_validator:
                st.subheader("Second-stage AI validation")
                vprompt = VALIDATION_PROMPT + "\n\nEXTRACTED JSON:\n" + json.dumps(data)
                with st.spinner("Validating extracted data..."):
                    vr = ask(vprompt, text_input, img, mime)
                try:
                    st.json(parse_json(vr))
                except ValueError:
                    st.code(vr)
        except Exception as e:
            st.error(f"Processing failed: {type(e).__name__}: {e}")
            if raw:
                with st.expander("Raw model output"):
                    st.code(raw)
            st.caption("Check API key, model name/access, billing, internet and image type.")

st.divider()
st.subheader("Prompt-engineering stages")
st.markdown("**V1:** baseline (Milestone 1) → **V2:** fixed JSON schema → "
            "**V3:** uncertainty safeguards → **V4:** strict rules + few-shot example, followed by a validation prompt.")
