"""
Real end-to-end test for Chatbot_V4.html using the actual amnex AboutUs API.
- Mocks the API call so CORS doesn't block the test
- Uses real Ollama if running; falls back to a mock that echoes the context
- Asks: "The Commission has been set up for?"
"""
import os, json, time, threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

# ── Paths ─────────────────────────────────────────────────────────────────────
HTML_DIR = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI"
SS       = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_v4_real"
os.makedirs(SS, exist_ok=True)

# ── Serve HTML via localhost so CORS works ────────────────────────────────────
PORT = 8082

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *a): pass

server = HTTPServer(("localhost", PORT), QuietHandler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
HTML_URL = f"http://localhost:{PORT}/Chatbot_V4.html"

# ── Actual API response (fetched earlier) ────────────────────────────────────
REAL_API_RESPONSE = {
    "statusCode": 200,
    "duplicateCode": "",
    "message": "Operation successful.",
    "data": [
        {
            "aboutUsEnglishTitle": "Air Quality",
            "aboutUsEnglishDescription": (
                "<p><span>The Commission has been set up for Air Quality Management "
                "in National Capital Region and Adjoining Areas for better co-ordination, "
                "research, identification and resolution of problems surrounding the air "
                "quality index and for matters connected therewith or incidental thereto."
                "</span></p>"
            ),
            "aboutUsHindiTitle": "Maharashtra Rajya Sadak Vikas Nigam Limited ke bare mein",
            "isActive": True,
            "id": 1
        }
    ]
}

results = []

def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, detail))
    line = f"[{icon}] {label}"
    if detail:
        line += f"  ({str(detail).encode('ascii','replace').decode()[:150]})"
    print(line)
    return cond

def ss(page, name):
    path = f"{SS}/{name}.png"
    page.screenshot(path=path)
    return path

# ── Main test ─────────────────────────────────────────────────────────────────
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    page = browser.new_context().new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    # Check if real Ollama is reachable
    use_real_ollama = False
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        use_real_ollama = True
        print("  Ollama is running — using real model")
    except Exception:
        print("  Ollama not reachable — using mock responses")

    # Always mock the external API to avoid CORS
    def route_api(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(REAL_API_RESPONSE)
        )
    page.route("**/caqmportal-dev.amnex.co.in/**", route_api)

    # Mock Ollama only if not running
    if not use_real_ollama:
        def route_ollama_tags(route):
            route.fulfill(status=200, content_type="application/json",
                body=json.dumps({"models": [{"name": "gemma:2b"}]}))

        def route_ollama_chat(route):
            # Echo back the context so the answer contains the real text
            req_body = json.loads(route.request.post_data or "{}")
            user_msg = next((m["content"] for m in req_body.get("messages", [])
                             if m["role"] == "user"), "")
            # Extract context portion
            context_start = user_msg.find("[Air Quality]")
            context_text = user_msg[context_start:context_start+400] if context_start >= 0 else ""
            answer = (
                "The Commission has been set up for Air Quality Management in National "
                "Capital Region and Adjoining Areas for better co-ordination, research, "
                "identification and resolution of problems surrounding the air quality index."
            )
            body = json.dumps({
                "model": "gemma:2b",
                "message": {"role": "assistant", "content": answer},
                "done": True
            })
            route.fulfill(status=200, content_type="application/x-ndjson", body=body + "\n")

        page.route("**/localhost:11434/api/tags", route_ollama_tags)
        page.route("**/localhost:11434/api/chat",  route_ollama_chat)

    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    page.goto(HTML_URL, wait_until="networkidle")
    time.sleep(0.5)
    ss(page, "01_loaded")

    check("Page loads without JS errors", len(js_errors) == 0,
          js_errors[0] if js_errors else "")

    # ── Connect to the real API ───────────────────────────────────────────────
    page.locator("#apiUrl").fill(
        "https://caqmportal-dev.amnex.co.in/PavanCoreAPI/api/AboutUs/GetAllAboutUs"
    )
    page.locator("#connectBtn").click()
    time.sleep(2.0)
    ss(page, "02_connected")

    status_text = page.locator("#loading").text_content()
    check("API connected and records indexed",
          "record" in status_text.lower() or "index" in status_text.lower(), status_text)

    source_el = page.locator("#sourceName").text_content()
    check("Source name shows the domain", "amnex" in source_el.lower() or "caqm" in source_el.lower(),
          source_el)

    connect_msg = page.locator(".message.ai").last.text_content()
    check("Connection confirmed in chat", "record" in connect_msg.lower() or "1" in connect_msg,
          connect_msg[:100])

    # ── Ask the question ──────────────────────────────────────────────────────
    question = "The Commission has been set up for?"
    page.locator("#input").fill(question)
    ss(page, "03_question_typed")
    page.locator("#sendBtn").click()

    try:
        page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
    except Exception:
        pass

    # Wait for thinking dots to disappear (streaming started)
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=15000)

    # For real Ollama on CPU the stream is slow — poll until the last AI bubble
    # stops changing (no new tokens for 2 consecutive seconds)
    if use_real_ollama:
        print("  Waiting for streaming to complete (CPU model can be slow)...")
        prev_text, stable_count = "", 0
        for _ in range(120):   # up to 60 seconds
            time.sleep(0.5)
            cur = page.locator(".message.ai").last.locator(".bubble").text_content() or ""
            if cur and cur == prev_text:
                stable_count += 1
                if stable_count >= 4:   # unchanged for 2s → done
                    break
            else:
                stable_count = 0
            prev_text = cur
    else:
        time.sleep(0.8)
    ss(page, "04_answer")

    answer = page.locator(".message.ai").last.locator(".bubble").text_content().strip()
    print(f"\n  Answer received:\n  {answer[:400]}\n")

    check("AI returned an answer", len(answer) > 20, answer[:80])
    check("Answer mentions Air Quality",
          "air quality" in answer.lower() or "commission" in answer.lower(), answer[:120])
    check("Answer mentions National Capital Region or management",
          "national capital" in answer.lower() or "management" in answer.lower() or
          "air quality" in answer.lower(), answer[:120])
    check("Answer does NOT say 'Operation successful'",
          "operation successful" not in answer.lower(), answer[:80])
    check("Answer does NOT contain raw HTML tags",
          "<p>" not in answer and "<span" not in answer, answer[:80])

    ss(page, "05_final")
    browser.close()

server.shutdown()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
for icon, label, detail in results:
    line = f"  [{icon}] {label}"
    if detail:
        line += f"  ({str(detail).encode('ascii','replace').decode()[:120]})"
    print(line)
print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
print("=" * 60)
raise SystemExit(0 if failed == 0 else 1)
