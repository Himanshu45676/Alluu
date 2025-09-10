import os
import sys
from typing import List, Dict

from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init
from openai import OpenAI


# Initialize color output for Windows terminals
colorama_init(autoreset=True)

# Load environment variables from .env if present
load_dotenv()


# Choose API key priority: OpenRouter > DeepSeek > OpenAI for compatibility
API_KEY = (
	os.getenv("OPENROUTER_API_KEY")
	or os.getenv("DEEPSEEK_API_KEY")
	or os.getenv("OPENAI_API_KEY")
	or ""
).strip()

# Base URL priority: OpenRouter > DeepSeek > default OpenAI (unused here)
BASE_URL = (
	os.getenv("OPENROUTER_BASE_URL")
	or os.getenv("DEEPSEEK_BASE_URL")
	or "https://openrouter.ai/api/v1"
).strip()

if not API_KEY:
	print(
		f"{Fore.RED}Missing API key. Set OPENROUTER_API_KEY (or DEEPSEEK_API_KEY / OPENAI_API_KEY)."
	)
	print(
		"Example (PowerShell): `setx OPENROUTER_API_KEY \"YOUR_KEY\"` then restart the shell."
	)
	sys.exit(1)

# Configure OpenAI-compatible SDK client (OpenRouter compatible)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Default chat model priority: OpenRouter > DeepSeek > OpenAI > fallback
DEFAULT_MODEL = (
	os.getenv("OPENROUTER_MODEL")
	or os.getenv("DEEPSEEK_MODEL")
	or os.getenv("OPENAI_MODEL")
	or "nousresearch/deephermes-3-llama-3-8b-preview:free"
)

# Optional OpenRouter ranking headers (see https://openrouter.ai/docs)
OPENROUTER_REFERER = os.getenv("OPENROUTER_SITE_URL", "").strip()
OPENROUTER_TITLE = os.getenv("OPENROUTER_SITE_NAME", "").strip()
EXTRA_HEADERS: Dict[str, str] = {}
if OPENROUTER_REFERER:
	EXTRA_HEADERS["HTTP-Referer"] = OPENROUTER_REFERER
if OPENROUTER_TITLE:
	EXTRA_HEADERS["X-Title"] = OPENROUTER_TITLE

SYSTEM_PROMPT = (
	"You are a helpful, concise assistant. Answer clearly and keep responses short when possible."
)


def print_assistant_prefix() -> None:
	print(f"{Fore.CYAN}Assistant{Style.RESET_ALL}: ", end="", flush=True)


def print_user_prefix() -> None:
	print(f"{Fore.GREEN}You{Style.RESET_ALL}: ", end="", flush=True)


def print_info(msg: str) -> None:
	print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")


def main() -> None:
	model = DEFAULT_MODEL
	messages: List[Dict[str, str]] = [
		{"role": "system", "content": SYSTEM_PROMPT},
	]

	print_info("Type '/exit' to quit, '/reset' to clear chat, '/model <name>' to switch model.")

	while True:
		print_user_prefix()
		try:
			user_input = input()
		except (EOFError, KeyboardInterrupt):
			print()  # newline
			break

		user_input = user_input.strip()
		if not user_input:
			continue

		# Commands
		if user_input.lower() in {"/exit", "exit", "quit", ":q"}:
			break
		if user_input.lower() == "/reset":
			messages = [{"role": "system", "content": SYSTEM_PROMPT}]
			print_info("Conversation reset.")
			continue
		if user_input.lower().startswith("/model"):
			parts = user_input.split(maxsplit=1)
			if len(parts) == 2 and parts[1]:
				model = parts[1].strip()
				print_info(f"Model set to: {model}")
			else:
				print_info(f"Current model: {model}")
			continue

		messages.append({"role": "user", "content": user_input})

		# Stream assistant response
		print_assistant_prefix()
		assistant_text_parts: List[str] = []
		try:
			stream = client.chat.completions.create(
				model=model,
				messages=messages,
				stream=True,
				**({"extra_headers": EXTRA_HEADERS} if EXTRA_HEADERS else {}),
			)
			for event in stream:
				delta = event.choices[0].delta
				content_piece = getattr(delta, "content", None)
				if content_piece:
					assistant_text_parts.append(content_piece)
					print(content_piece, end="", flush=True)
			print()  # newline after the stream completes
		except Exception as exc:
			print(f"\n{Fore.RED}[error]{Style.RESET_ALL} {exc}")
			# Remove the last user message on failure to avoid poisoning context
			messages.pop()
			continue

		assistant_text = "".join(assistant_text_parts)
		messages.append({"role": "assistant", "content": assistant_text})

	print_info("Goodbye 👋")


if __name__ == "__main__":
	main()
