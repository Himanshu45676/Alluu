import os
from typing import List, Dict

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = (
	os.getenv("OPENROUTER_API_KEY")
	or os.getenv("DEEPSEEK_API_KEY")
	or os.getenv("OPENAI_API_KEY")
	or ""
).strip()
BASE_URL = (
	os.getenv("OPENROUTER_BASE_URL")
	or os.getenv("DEEPSEEK_BASE_URL")
	or "https://openrouter.ai/api/v1"
).strip()
DEFAULT_MODEL = (
	os.getenv("OPENROUTER_MODEL")
	or os.getenv("DEEPSEEK_MODEL")
	or os.getenv("OPENAI_MODEL")
	or "nousresearch/deephermes-3-llama-3-8b-preview:free"
)

st.set_page_config(page_title="AI Chat", page_icon="💬", layout="centered")
st.title("AI Chat UI 💬")

with st.sidebar:
	st.header("Settings")
	api_key_input = st.text_input("API Key", value=API_KEY, type="password")
	base_url_input = st.text_input("Base URL", value=BASE_URL)
	model_input = st.text_input("Model", value=DEFAULT_MODEL)
	referer = st.text_input("HTTP-Referer (optional)", value=os.getenv("OPENROUTER_SITE_URL", ""))
	title = st.text_input("X-Title (optional)", value=os.getenv("OPENROUTER_SITE_NAME", ""))
	clear = st.button("Clear Conversation")

if clear or "messages" not in st.session_state:
	st.session_state.messages: List[Dict[str, str]] = [
		{"role": "system", "content": "You are a helpful, concise assistant."}
	]

if not api_key_input:
	st.info("Enter an API key in the sidebar to begin.")
	st.stop()

client = OpenAI(api_key=api_key_input, base_url=base_url_input)
extra_headers: Dict[str, str] = {}
if referer:
	extra_headers["HTTP-Referer"] = referer
if title:
	extra_headers["X-Title"] = title

for m in st.session_state.messages:
	if m["role"] == "user":
		with st.chat_message("user"):
			st.markdown(m["content"])
	elif m["role"] == "assistant":
		with st.chat_message("assistant"):
			st.markdown(m["content"])

prompt = st.chat_input("Type a message")
if prompt:
	st.session_state.messages.append({"role": "user", "content": prompt})
	with st.chat_message("user"):
		st.markdown(prompt)

	with st.chat_message("assistant"):
		placeholder = st.empty()
		accum = []
		try:
			stream = client.chat.completions.create(
				model=model_input,
				messages=st.session_state.messages,
				stream=True,
				**({"extra_headers": extra_headers} if extra_headers else {}),
			)
			for event in stream:
				delta = event.choices[0].delta
				content_piece = getattr(delta, "content", None)
				if content_piece:
					accum.append(content_piece)
					placeholder.markdown("".join(accum))
			assistant_text = "".join(accum)
		except Exception as exc:
			assistant_text = f"[error] {exc}"
			placeholder.markdown(assistant_text)

	st.session_state.messages.append({"role": "assistant", "content": assistant_text})
