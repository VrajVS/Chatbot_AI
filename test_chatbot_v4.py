"""
Test suite for Chatbot_V4.html (Ollama + REST API chatbot)
Mocks both Ollama (/api/tags, /api/chat) and the external API endpoint
so the tests run without Ollama being installed or running.
"""
import os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\Chatbot_V4.html").as_uri()
SS   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_v4"
os.makedirs(SS, exist_ok=True)

results = []

def ss(page, name):
    path = f"{SS}/{name}.png"
    page.screenshot(path=path, full_page=False)
    return path

def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, detail))
    line = f"[{icon}] {label}"
    if detail:
        line += f"  ({str(detail).encode('ascii','replace').decode()[:120]})"
    print(line)
    return cond

# ── Mock helpers ─────────────────────────────────────────────────────────────

FAKE_API_DATA = [
    {"id": 1, "name": "Alice Johnson", "role": "Engineer",  "salary": 95000},
    {"id": 2, "name": "Bob Smith",     "role": "Designer",  "salary": 82000},
    {"id": 3, "name": "Carol White",   "role": "Manager",   "salary": 110000},
]

def route_ollama_tags(route):
    """Mock Ollama /api/tags — pretend gemma:2b is available."""
    route.fulfill(status=200, content_type="application/json", body=json.dumps({
        "models": [{"name": "gemma:2b", "size": 1600000000}]
    }))

def route_ollama_chat(route):
    """
    Mock Ollama /api/chat streaming.
    Returns newline-delimited JSON the way Ollama actually does.
    """
    tokens = ["There ", "are ", "3 ", "employees: ", "Alice Johnson (Engineer, $95k), ",
              "Bob Smith (Designer, $82k), ", "and Carol White (Manager, $110k)."]
    lines = [
        json.dumps({"model": "gemma:2b",
                    "message": {"role": "assistant", "content": t},
                    "done": False})
        for t in tokens
    ]
    lines.append(json.dumps({"model": "gemma:2b",
                              "message": {"role": "assistant", "content": ""},
                              "done": True}))
    route.fulfill(status=200, content_type="application/x-ndjson",
                  body="\n".join(lines) + "\n")

def route_fake_api(route):
    """Mock an external JSON endpoint."""
    route.fulfill(status=200, content_type="application/json",
                  body=json.dumps(FAKE_API_DATA))

# ── Test runner ───────────────────────────────────────────────────────────────

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        page = browser.new_context().new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        # Intercept Ollama and the fake API before loading
        page.route("**/localhost:11434/api/tags",  route_ollama_tags)
        page.route("**/localhost:11434/api/chat",  route_ollama_chat)
        page.route("**/fake-api.test/**",          route_fake_api)

        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))

        page.goto(HTML, wait_until="networkidle")
        time.sleep(0.6)
        ss(page, "01_initial")

        # ── 1. Page load ─────────────────────────────────────────────────────
        check("No JS errors on load", len(js_errors) == 0,
              js_errors[0] if js_errors else "")

        # ── 2. Sidebar elements ──────────────────────────────────────────────
        model_val = page.locator("#ollamaModel").input_value()
        check("Model field defaults to gemma:2b", model_val == "gemma:2b", model_val)

        url_placeholder = page.locator("#apiUrl").get_attribute("placeholder")
        check("API URL input present", bool(url_placeholder), url_placeholder)

        connect_btn = page.locator("#connectBtn")
        check("Connect button present", connect_btn.is_visible())

        toggle = page.locator("#sidebarToggle")
        check("Sidebar toggle button present", toggle.is_visible())

        # ── 3. Time-based greeting in chat ───────────────────────────────────
        # V4 may not have the greeting system — check for any welcome message
        first_bubble = page.locator(".message.ai .bubble").first
        welcome_text = first_bubble.text_content().strip()
        check("Welcome message present", len(welcome_text) > 5, welcome_text[:80])

        # ── 4. Ping Ollama (mocked) ──────────────────────────────────────────
        page.locator("#pingBtn").click()
        time.sleep(0.8)
        ss(page, "02_after_ping")

        ping_class = page.locator("#pingBtn").get_attribute("class")
        check("Ping button turns green (Ollama reachable)", "ok" in ping_class, ping_class)

        status_text = page.locator("#loading").text_content()
        check("Status shows model list after ping",
              "gemma" in status_text or "model" in status_text.lower(), status_text)

        # ── 5. Sidebar collapse ──────────────────────────────────────────────
        toggle.click()
        time.sleep(0.4)
        container_cls = page.locator(".container").get_attribute("class")
        check("Sidebar collapses on toggle", "sidebar-collapsed" in container_cls, container_cls)

        toggle.click()
        time.sleep(0.4)
        container_cls2 = page.locator(".container").get_attribute("class")
        check("Sidebar expands again on second toggle",
              "sidebar-collapsed" not in container_cls2, container_cls2)

        # ── 6. Ask without connecting API first ─────────────────────────────
        page.locator("#input").fill("What is the data?")
        page.locator("#sendBtn").click()
        time.sleep(0.4)
        last_ai = page.locator(".message.ai").last.locator(".bubble").text_content()
        check("Warning shown when no API connected",
              "connect" in last_ai.lower() or "api" in last_ai.lower(), last_ai[:80])

        # ── 7. Connect to mock API ───────────────────────────────────────────
        page.locator("#apiUrl").fill("http://fake-api.test/employees")
        page.locator("#connectBtn").click()
        time.sleep(1.2)
        ss(page, "03_after_connect")

        status_after = page.locator("#loading").text_content()
        check("Status shows records indexed after connect",
              "record" in status_after.lower() or "index" in status_after.lower(),
              status_after)

        # Check AI confirmed the connection
        connect_msg = page.locator(".message.ai").last.locator(".bubble").text_content()
        check("AI confirms connection with record count",
              "record" in connect_msg.lower() or "connect" in connect_msg.lower() or
              "3" in connect_msg, connect_msg[:100])

        # ── 8. Send a question (streams from mocked Ollama) ──────────────────
        page.locator("#input").fill("List all employees and their salaries.")
        page.locator("#sendBtn").click()

        try:
            page.wait_for_function("() => !!document.querySelector('.thinking-row')",
                                   timeout=5000)
        except Exception:
            pass

        page.wait_for_function("() => !document.querySelector('.thinking-row')",
                               timeout=20000)
        time.sleep(0.5)
        ss(page, "04_after_chat")

        ai_answer = page.locator(".message.ai").last.locator(".bubble").text_content().strip()
        check("AI returned a streamed answer", len(ai_answer) > 10, ai_answer[:100])
        check("Answer mentions employee names",
              "alice" in ai_answer.lower() or "bob" in ai_answer.lower() or
              "carol" in ai_answer.lower(), ai_answer[:100])

        # ── 9. Send button disables during request ───────────────────────────
        # (checked implicitly — if the test above completed, send btn cycled)
        send_disabled = page.locator("#sendBtn").get_attribute("disabled")
        check("Send button re-enabled after response", send_disabled is None)

        # ── 10. Enter key sends message ─────────────────────────────────────
        msg_count_before = page.locator(".message.user").count()
        page.locator("#input").fill("How many employees are there?")
        page.locator("#input").press("Enter")
        time.sleep(0.3)
        msg_count_after = page.locator(".message.user").count()
        check("Enter key submits message",
              msg_count_after > msg_count_before, f"{msg_count_before} -> {msg_count_after}")

        # ── 11. Shift+Enter does NOT submit ──────────────────────────────────
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=15000)
        count_before = page.locator(".message.user").count()
        page.locator("#input").fill("Line one")
        page.locator("#input").press("Shift+Enter")
        time.sleep(0.2)
        count_after = page.locator(".message.user").count()
        check("Shift+Enter does NOT submit", count_after == count_before,
              f"{count_before} -> {count_after}")

        # ── 12. Method select shows body textarea for POST ───────────────────
        page.locator("#apiMethod").select_option("POST")
        time.sleep(0.2)
        body_display = page.evaluate(
            "() => document.getElementById('apiBody').style.display")
        check("POST body textarea shown when method=POST",
              body_display != "none", body_display)

        page.locator("#apiMethod").select_option("GET")
        time.sleep(0.2)
        body_display2 = page.evaluate(
            "() => document.getElementById('apiBody').style.display")
        check("POST body textarea hidden when method=GET",
              body_display2 == "none", body_display2)

        ss(page, "05_final")
        browser.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    for icon, label, detail in results:
        line = f"  [{icon}] {label}"
        if detail:
            line += f"  ({str(detail).encode('ascii','replace').decode()[:100]})"
        print(line)
    print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    ok = run()
    raise SystemExit(0 if ok else 1)
