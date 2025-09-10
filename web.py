import os
from typing import List, Dict

from flask import Flask, render_template_string, request, session, jsonify, redirect, url_for
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
# Session defaults
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

LOCK_PASSWORD = os.getenv("LOCK_PASSWORD", "230111009115")
# Controls lock behavior
LOCK_ON_RELOAD = os.getenv("LOCK_ON_RELOAD", "1")  # "1" => show lock every reload
LOCK_PERSIST = os.getenv("LOCK_PERSIST", "0")      # "1" => remember unlock in cookie session

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
REFERER = os.getenv("OPENROUTER_SITE_URL", "").strip()
TITLE = os.getenv("OPENROUTER_SITE_NAME", "").strip()
EXTRA_HEADERS: Dict[str, str] = {}
if REFERER:
	EXTRA_HEADERS["HTTP-Referer"] = REFERER
if TITLE:
	EXTRA_HEADERS["X-Title"] = TITLE

client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY else None

LANDING_TEMPLATE = """
<!doctype html>
<html>
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
	<title>potato.ai • Welcome</title>
	<style>
		:root { --bg1:#1b140d; --bg2:#0f0b07; --text:#f6efe7; --muted:#d1b89a; --edge:#2b1e12; --accent:#b7832f; --accent2:#d4a052; }
		html, body { height:100%; }
		body { margin:0; background: radial-gradient(1200px 600px at 80% -10%, #d4a05222, transparent), linear-gradient(140deg, var(--bg1), var(--bg2)); color:var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }
		.hero { min-height:100%; display:grid; grid-template-rows: auto 1fr auto; }
		.nav { display:flex; align-items:center; justify-content:space-between; padding:16px 22px; border-bottom:1px solid var(--edge); }
		.brand { display:flex; align-items:center; gap:10px; font-weight:700; letter-spacing:.35px; }
		.logo { width:28px; height:28px; border-radius:7px; display:grid; place-items:center; background: radial-gradient(circle at 35% 30%, #e6b76a, #b27b34 60%, #885a1f); box-shadow: 0 10px 30px #b27b3433; }
		.cta { display:flex; gap:10px; }
		.cta a { text-decoration:none; color:var(--text); border:1px solid var(--edge); padding:8px 12px; border-radius:10px; }
		.main { display:grid; place-items:center; text-align:center; padding: 44px 20px; }
		.h1 { font-size: clamp(28px, 6vw, 48px); line-height:1.1; font-weight:900; margin:0; letter-spacing:.3px; }
		.sub { margin-top:12px; color:var(--muted); max-width:860px; }
		.grid { margin-top:28px; display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px; max-width:1000px; width:100%; }
		.card { background:#21170e; border:1px solid var(--edge); border-radius:16px; padding:14px; text-align:left; }
		.card h3 { margin:0 0 6px 0; font-size:15px; }
		.card p { margin:0; color:var(--muted); font-size:13px; }
		.actions { margin-top:30px; display:flex; gap:12px; justify-content:center; }
		.btn { background: linear-gradient(180deg, var(--accent2), var(--accent)); color:white; border:0; padding: 12px 16px; border-radius: 12px; cursor:pointer; font-weight:800; box-shadow: 0 10px 24px #d4a05233; text-decoration:none; }
		.btn.secondary { background: transparent; border:1px solid var(--edge); color:var(--text); }
		.footer { padding:14px 22px; border-top:1px solid var(--edge); color:var(--muted); font-size:12px; }
	</style>
</head>
<body>
	<div class=\"hero\">
		<div class=\"nav\">
			<div class=\"brand\"><div class=\"logo\">🥔</div> potato.ai</div>
			<div class=\"cta\"><a href=\"/chat\">Open Chat</a></div>
		</div>
		<div class=\"main\">
			<h1 class=\"h1\">Build, explore, and deploy with AI — the potato way</h1>
			<p class=\"sub\">potato.ai is a unified chat interface powered by OpenRouter-compatible models. Write code with one-click copy, get well-formatted answers, and switch models seamlessly. Your session is protected by a lock screen and themed UI.</p>
			<div class=\"grid\">
				<div class=\"card\"><h3>Multi-Provider</h3><p>Works with OpenRouter, DeepSeek, or OpenAI-compatible endpoints.</p></div>
				<div class=\"card\"><h3>Code First</h3><p>Markdown rendering, syntax highlighting, and one-click copy for code blocks.</p></div>
				<div class=\"card\"><h3>Fast UX</h3><p>Typing animation and smooth, responsive chat experience.</p></div>
				<div class=\"card\"><h3>Secure</h3><p>Optional lock screen gate; server-side API key usage.</p></div>
			</div>
			<div class=\"actions\">
				<a class=\"btn\" href=\"/chat\">Get Started</a>
				<a class=\"btn secondary\" href=\"https://openrouter.ai\" target=\"_blank\" rel=\"noreferrer\">Docs</a>
			</div>
		</div>
		<div class=\"footer\">© {{ year }} potato.ai • Model default: {{ default_model }}</div>
	</div>
</body>
</html>
"""

CHAT_TEMPLATE = """
<!doctype html>
<html>
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
	<title>potato.ai</title>
	<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css\">
	<style>
		:root {
			--bg1:#1b140d; --bg2:#0f0b07; --card:#241a11; --edge:#362617;
			--text:#f6efe7; --muted:#d1b89a; --accent:#b7832f; --accent2:#d4a052;
		}
		html, body { height: 100%; }
		body {
			margin: 0; color: var(--text);
			font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
			background:
				radial-gradient(1000px 500px at 80% -10%, #d4a05222, transparent),
				linear-gradient(140deg, var(--bg1), var(--bg2));
		}
		.app { display:flex; flex-direction:column; height:100%; }
		.header { padding: 14px 18px; position: sticky; top:0; backdrop-filter: blur(8px); background: #160f09cc; border-bottom:1px solid #2b1e12; display:flex; align-items:center; gap:10px; }
		.logo { width:28px; height:28px; border-radius:7px; display:grid; place-items:center; background: radial-gradient(circle at 35% 30%, #e6b76a, #b27b34 60%, #885a1f); box-shadow: 0 10px 30px #b27b3433; font-size:16px; }
		.title { font-size: 14px; color:#f4dfc7; letter-spacing: .35px; font-weight:600; }
		.watermark { margin-left:auto; font-size:12px; color: var(--muted); opacity:.7; }
		.chat { flex:1; overflow-y:auto; padding: 18px; scroll-behavior:smooth; }
		.card { background: var(--card); border:1px solid var(--edge); border-radius: 14px; padding: 12px 14px; margin: 8px 0; max-width: 85%; animation: fadeIn .3s ease-out; }
		.card :is(p, ul, ol, pre, code) { white-space: pre-wrap; word-wrap: break-word; }
		.card pre { position: relative; padding-top: 34px; }
		.copy-btn { position:absolute; top:8px; right:8px; background:#5b4228; color:#f6efe7; border:1px solid #714f2c; border-radius:8px; padding:6px 8px; font-size:12px; cursor:pointer; }
		.copy-btn:active { transform: translateY(1px); }
		@keyframes fadeIn { from { opacity:0; transform: translateY(6px);} to { opacity:1; transform: translateY(0);} }
		.row { display:flex; gap:10px; align-items:flex-start; }
		.msg-user { margin-left:auto; background: #2a1f12; border-color:#3a2a17; box-shadow: 0 8px 24px #b27b3414; }
		.msg-assistant { margin-right:auto; background: #21170e; border-color:#2e1f13; box-shadow: 0 8px 24px #00000022; }
		.footer { position: sticky; bottom:0; padding: 12px 18px; background:#160f09cc; backdrop-filter: blur(8px); border-top:1px solid #2b1e12; }
		.input { display:flex; gap:10px; }
		input[type=text] { flex:1; padding: 12px 14px; border-radius: 12px; border:1px solid var(--edge); background:#1a120b; color: var(--text); outline:none; transition: border .2s, box-shadow .2s; }
		input[type=text]:focus { border-color:var(--accent2); box-shadow: 0 0 0 4px #d4a05222; }
		button { background: linear-gradient(180deg, var(--accent2), var(--accent)); color:white; border:0; padding: 12px 16px; border-radius: 12px; cursor:pointer; font-weight:700; box-shadow: 0 10px 24px #d4a05233; transition: transform .06s ease; }
		button:active { transform: translateY(1px); }
		.typing { display:inline-flex; gap:4px; align-items:center; padding:6px 8px; }
		.dot { width:6px; height:6px; border-radius:50%; background:#d4a052; opacity:.6; animation: bounce 1s infinite ease-in-out; }
		.dot:nth-child(2){ animation-delay:.15s } .dot:nth-child(3){ animation-delay:.3s }
		@keyframes bounce{ 0%,80%,100%{ transform: translateY(0); opacity:.35} 40%{ transform: translateY(-5px); opacity:.9} }
		a { color:#d4a052; }

		/* Lock screen */
		.lock { position: fixed; inset: 0; background: #0b0b0fb3; backdrop-filter: blur(6px); display: {{ 'none' if unlocked else 'grid' }}; place-items: center; z-index: 50; }
		.lock-card { width: 92%; max-width: 380px; background: #1c140d; border:1px solid #362617; border-radius: 16px; padding: 18px; box-shadow: 0 20px 50px #00000055; }
		.lock-title { font-weight: 700; letter-spacing:.3px; margin-bottom: 10px; color:#f4dfc7; }
		.lock-input { width: 100%; padding: 12px 14px; border-radius: 12px; border:1px solid #3a2a17; background:#140e0a; color: #f6efe7; outline:none; }
		.lock-input:focus { border-color:#d4a052; box-shadow: 0 0 0 4px #d4a05222; }
		.lock-btn { margin-top: 10px; width: 100%; padding: 12px 16px; border-radius: 12px; border:0; background: linear-gradient(180deg, var(--accent2), var(--accent)); color:white; font-weight:700; cursor:pointer; }
		.lock-msg { margin-top: 8px; color:#d1b89a; font-size:12px; min-height: 18px; }
	</style>
</head>
<body>
	<div class=\"app\" aria-hidden=\"{{ 'true' if not unlocked else 'false' }}\">
		<div class=\"header\">
			<div class=\"logo\">🥔</div>
			<div class=\"title\">potato.ai</div>
			<div class=\"watermark\">potato.ai • Model: {{ (session.get('model') or default_model) }}</div>
		</div>
		<div id=\"chat\" class=\"chat\">
			{% for m in messages %}
				<div class=\"row\">
					<div class=\"card {{ 'msg-user' if m.role=='user' else 'msg-assistant' }}\"><div class=\"md\" data-role=\"{{ m.role }}\">{{ m.content }}</div></div>
				</div>
			{% endfor %}
		</div>
		<div class=\"footer\">
			<form id=\"send-form\" class=\"input\" autocomplete=\"off\">
				<input id=\"prompt\" type=\"text\" placeholder=\"Ask anything...\" />
				<button type=\"submit\">Send</button>
			</form>
		</div>
	</div>

	<div class=\"lock\" id=\"lock\">
		<div class=\"lock-card\">
			<div class=\"lock-title\">Enter Passcode</div>
			<input id=\"lock-input\" class=\"lock-input\" type=\"password\" placeholder=\"Password\" autofocus />
			<button id=\"lock-btn\" class=\"lock-btn\">Unlock</button>
			<div id=\"lock-msg\" class=\"lock-msg\"></div>
		</div>
	</div>

	<script src=\"https://cdn.jsdelivr.net/npm/marked/marked.min.js\"></script>
	<script src=\"https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/common.min.js\"></script>
	<script>
		const chat = document.getElementById('chat');
		const form = document.getElementById('send-form');
		const promptInput = document.getElementById('prompt');

		function enhanceCodeBlocks(container){
			container.querySelectorAll('pre code').forEach((code)=>{
				const pre = code.parentElement;
				const btn = document.createElement('button');
				btn.className = 'copy-btn';
				btn.type = 'button';
				btn.textContent = 'Copy';
				btn.addEventListener('click', async ()=>{
					try{ await navigator.clipboard.writeText(code.textContent); btn.textContent='Copied'; setTimeout(()=>btn.textContent='Copy', 1200);}catch(e){ btn.textContent='Failed'; setTimeout(()=>btn.textContent='Copy', 1200);} 
				});
				pre.style.position = 'relative';
				pre.prepend(btn);
			});
		}

		function renderMarkdown(text){
			const html = marked.parse(text, { breaks:true });
			const wrapper = document.createElement('div');
			wrapper.innerHTML = html;
			wrapper.querySelectorAll('pre code').forEach((block)=>{ try{ hljs.highlightElement(block);}catch(e){} });
			enhanceCodeBlocks(wrapper);
			return wrapper.innerHTML;
		}

		function addMessage(role, content){
			const row = document.createElement('div');
			row.className = 'row';
			const card = document.createElement('div');
			card.className = 'card ' + (role === 'user' ? 'msg-user' : 'msg-assistant');
			const md = document.createElement('div');
			md.className = 'md';
			md.innerHTML = renderMarkdown(content);
			card.appendChild(md);
			row.appendChild(card);
			chat.appendChild(row);
			chat.scrollTop = chat.scrollHeight;
		}

		function addTyping(){
			const row = document.createElement('div');
			row.className = 'row';
			row.id = 'typing-row';
			const card = document.createElement('div');
			card.className = 'card msg-assistant';
			card.innerHTML = '<div class="typing"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
			row.appendChild(card);
			chat.appendChild(row);
			chat.scrollTop = chat.scrollHeight;
		}

		function removeTyping(){
			const t = document.getElementById('typing-row');
			if(t){ t.remove(); }
		}

		// Render any existing messages (server-rendered content is plain text)
		document.querySelectorAll('.md').forEach((el)=>{ el.innerHTML = renderMarkdown(el.textContent); });

		form.addEventListener('submit', async (e)=>{
			e.preventDefault();
			const text = promptInput.value.trim();
			if(!text) return;
			addMessage('user', text);
			promptInput.value = '';
			addTyping();
			try{
				const res = await fetch('/send_json', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ prompt: text }) });
				const data = await res.json();
				removeTyping();
				addMessage('assistant', data.assistant || '[no response]');
			}catch(err){
				removeTyping();
				addMessage('assistant', '[error] ' + err);
			}
		});

		// Lock handling
		const lockEl = document.getElementById('lock');
		const lockInput = document.getElementById('lock-input');
		const lockBtn = document.getElementById('lock-btn');
		const lockMsg = document.getElementById('lock-msg');
		async function tryUnlock(){
			const pw = (lockInput.value||'').trim();
			if(!pw) return;
			lockBtn.disabled = true;
			lockMsg.textContent = 'Checking...';
			try{
				const r = await fetch('/unlock', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ password: pw }) });
				const j = await r.json();
				if(j.ok){ lockEl.style.display='none'; }
				else { lockMsg.textContent = 'Incorrect password'; }
			} catch(e){ lockMsg.textContent = 'Error'; }
			lockBtn.disabled = false;
		}
		lockBtn.addEventListener('click', (e)=>{ e.preventDefault(); tryUnlock(); });
		lockInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){ e.preventDefault(); tryUnlock(); } });
	</script>
</body>
</html>
"""


def ensure_messages() -> List[Dict[str, str]]:
	if "messages" not in session:
		session["messages"] = [
			{"role": "system", "content": "You are a helpful, concise assistant."}
		]
	return session["messages"]


def get_headers() -> Dict[str, str]:
	headers: Dict[str, str] = {}
	if REFERER:
		headers["HTTP-Referer"] = REFERER
	if TITLE:
		headers["X-Title"] = TITLE
	return headers


@app.route("/", methods=["GET"])
def landing():
	return render_template_string(LANDING_TEMPLATE, year=__import__('datetime').datetime.now().year, default_model=DEFAULT_MODEL)


@app.route("/chat", methods=["GET"])
def chat_page():
	messages = ensure_messages()
	# If LOCK_ON_RELOAD is enabled (default), force lock on each load
	if LOCK_ON_RELOAD == "1":
		session["unlocked"] = False
	return render_template_string(
		CHAT_TEMPLATE,
		messages=messages,
		default_model=DEFAULT_MODEL,
		unlocked=session.get("unlocked", False),
	)


@app.route("/send_json", methods=["POST"])
def send_json():
	if not session.get("unlocked", False):
		return jsonify({"assistant": "[locked] Please unlock to chat"})
	if not client:
		return jsonify({"assistant": "[error] Missing API key on server"})
	payload = request.get_json(silent=True) or {}
	prompt = (payload.get("prompt") or "").strip()
	if not prompt:
		return jsonify({"assistant": ""})
	messages = ensure_messages()
	messages.append({"role": "user", "content": prompt})
	try:
		resp = client.chat.completions.create(
			model=session.get("model") or DEFAULT_MODEL,
			messages=messages,
			stream=False,
			**({"extra_headers": get_headers()} if get_headers() else {}),
		)
		assistant_text = resp.choices[0].message.content or ""
	except Exception as exc:
		assistant_text = f"[error] {exc}"
	messages.append({"role": "assistant", "content": assistant_text})
	session["messages"] = messages
	return jsonify({"assistant": assistant_text})


@app.route("/unlock", methods=["POST"])
def unlock():
	payload = request.get_json(silent=True) or {}
	password = (payload.get("password") or "").strip()
	if password == LOCK_PASSWORD:
		if LOCK_PERSIST == "1":
			session.permanent = True
		session["unlocked"] = True
		return jsonify({"ok": True})
	return jsonify({"ok": False})


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True)
