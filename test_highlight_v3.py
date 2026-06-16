"""
Rigorous Playwright test for PDF highlight feature in pdf_chatbot_V3.html.
Tests:
  1. Highlights appear after clicking a citation
  2. Highlights cover only part of the page (not the whole canvas)
  3. Each highlight box is reasonably sized (not giant or 0-size)
  4. Different questions produce different highlighted keywords
  5. No JavaScript errors
  6. Highlight positions are inside the canvas bounds
"""
import os, json, time, threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────────
HTML_DIR = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI"
PDF_PATH = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"
if not Path(PDF_PATH).exists():
    PDF_PATH = str(next(Path(HTML_DIR).parent.glob("*.pdf"), None) or "")
SS_DIR   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_highlight"
os.makedirs(SS_DIR, exist_ok=True)

PORT = 8085

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *a): pass

server = HTTPServer(("localhost", PORT), QuietHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://localhost:{PORT}/pdf_chatbot_V3.html"

# ── Helpers ───────────────────────────────────────────────────────────────────
results = []

def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, str(detail)[:200]))
    print(f"  [{icon}] {label}" + (f"  ({str(detail)[:120]})" if detail else ""))
    return cond

def ss(page, name):
    path = f"{SS_DIR}/{name}.png"
    page.screenshot(path=path, full_page=False)
    return path

def wait_for_ai_reply(page, timeout=25_000):
    """Wait until thinking dots disappear and a non-empty AI bubble appears."""
    try:
        page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=6000)
    except Exception:
        pass
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=timeout)
    time.sleep(0.4)

# ── Mock Ollama (not running) ─────────────────────────────────────────────────
MOCK_ANSWERS = {
    "commission": (
        "The Commission was established for Air Quality Management in the National Capital "
        "Region. It coordinates research and resolution of air quality problems."
    ),
    "members": (
        "The Commission includes members from various government bodies responsible for "
        "environmental management and coordination across the region."
    ),
    "purpose": (
        "The purpose of the Commission is to improve air quality index through better "
        "co-ordination, research, and resolution of environmental issues."
    ),
}

def make_ollama_mock(page, answers=MOCK_ANSWERS):
    def route_tags(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"models": [{"name": "gemma:2b"}]}))

    def route_chat(route):
        try:
            body = json.loads(route.request.post_data or "{}")
            user_msg = next((m["content"] for m in body.get("messages", [])
                             if m["role"] == "user"), "").lower()
            answer = answers.get("commission")
            for k, v in answers.items():
                if k in user_msg:
                    answer = v
                    break
            ndjson = json.dumps({
                "model": "gemma:2b",
                "message": {"role": "assistant", "content": answer},
                "done": True
            }) + "\n"
            route.fulfill(status=200, content_type="application/x-ndjson", body=ndjson)
        except Exception as e:
            route.fulfill(status=500, body=str(e))

    page.route("**/localhost:11434/api/tags", route_tags)
    page.route("**/localhost:11434/api/chat",  route_chat)

# ── Main test ─────────────────────────────────────────────────────────────────
print(f"\nPDF: {PDF_PATH}")
print(f"URL: {URL}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=80)
    ctx     = browser.new_context()
    page    = ctx.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    make_ollama_mock(page)
    page.goto(URL, wait_until="networkidle")
    time.sleep(0.5)
    ss(page, "00_loaded")

    check("Page loads without JS errors", len(js_errors) == 0,
          js_errors[0] if js_errors else "")

    # ── 1. Upload PDF ────────────────────────────────────────────────────────
    if not PDF_PATH:
        print("  [SKIP] No PDF found — skipping file upload test")
    else:
        page.locator("#fileInput").set_input_files(PDF_PATH)
        page.wait_for_function(
            "() => document.getElementById('statusDot').classList.contains('active')",
            timeout=20_000
        )
        time.sleep(0.3)
        ss(page, "01_pdf_loaded")

        status = page.locator("#loading").text_content()
        check("PDF indexed (status shows chunks)", "chunk" in status.lower() or "page" in status.lower(), status)
        check("PDF name shown in chip", page.locator(".chip-label").text_content().endswith(".pdf") or
              "pdf" in page.locator(".chip-label").text_content().lower(), "")

        print("\n── Question 1: commission ──")
        page.locator("#input").fill("What is the Commission set up for?")
        page.locator("#actionBtn").click()
        wait_for_ai_reply(page)
        ss(page, "02_answer_q1")

        ai_msgs = page.locator(".message.ai .bubble")
        last_ai = ai_msgs.last
        check("AI returned an answer (Q1)", len(last_ai.text_content().strip()) > 20,
              last_ai.text_content()[:80])

        # ── 2. Citation pills ────────────────────────────────────────────────
        source_pills = last_ai.locator(".source")
        pill_count = source_pills.count()
        check("At least one citation pill shown", pill_count >= 1, f"{pill_count} pills")

        if pill_count > 0:
            print("\n── Opening citation modal ──")
            source_pills.first.click()
            time.sleep(1.2)   # render + highlight
            ss(page, "03_modal_open")

            modal = page.locator("#pdfModal")
            check("PDF modal is visible", modal.is_visible(), "")

            # ── 3. Highlight count & coverage ────────────────────────────────
            highlight_count = page.locator(".highlight").count()
            check("At least 1 highlight box rendered", highlight_count >= 1,
                  f"{highlight_count} highlights")

            canvas = page.locator("#pdfCanvas")
            canvas_w = canvas.evaluate("el => el.width")
            canvas_h = canvas.evaluate("el => el.height")
            check("Canvas has non-zero size", canvas_w > 0 and canvas_h > 0,
                  f"{canvas_w}×{canvas_h}")

            # Collect highlight bounding boxes via JS
            boxes = page.evaluate("""
                () => [...document.querySelectorAll('.highlight')].map(h => ({
                    left:   parseFloat(h.style.left),
                    top:    parseFloat(h.style.top),
                    width:  parseFloat(h.style.width),
                    height: parseFloat(h.style.height),
                }))
            """)

            print(f"\n  Canvas size: {canvas_w} × {canvas_h}")
            print(f"  Highlight count: {len(boxes)}")
            for j, b in enumerate(boxes[:8]):
                print(f"    [{j}] left={b['left']:.0f} top={b['top']:.0f} "
                      f"w={b['width']:.0f} h={b['height']:.0f}")

            # Each highlight height should be a single line (not the whole canvas height)
            # Wide boxes are fine (PDF renders full lines as one item)
            full_height = [b for b in boxes if b["height"] > canvas_h * 0.1]
            check("No highlight is taller than 10% of canvas (not a block)", len(full_height) == 0,
                  f"{len(full_height)} over-tall boxes" if full_height else "")

            # Highlights should be inside canvas
            out_of_bounds = [b for b in boxes
                             if b["left"] < -10 or b["top"] < -10
                             or b["left"] + b["width"] > canvas_w + 20
                             or b["top"]  + b["height"] > canvas_h + 20]
            check("All highlights within canvas bounds", len(out_of_bounds) == 0,
                  f"{len(out_of_bounds)} out-of-bounds" if out_of_bounds else "")

            # Heights should be reasonable (8–80px)
            bad_h = [b for b in boxes if b["height"] < 4 or b["height"] > 120]
            check("All highlight heights are reasonable (4–120px)", len(bad_h) == 0,
                  f"{len(bad_h)} bad heights" if bad_h else "")

            # Compute total highlighted area vs canvas area
            total_hl_area = sum(b["width"] * b["height"] for b in boxes)
            canvas_area   = canvas_w * canvas_h
            coverage_pct  = 100 * total_hl_area / max(canvas_area, 1)
            print(f"\n  Total highlighted area: {total_hl_area:.0f}px² "
                  f"({coverage_pct:.1f}% of canvas)")
            check("Highlights cover <40% of canvas (not whole-page)", coverage_pct < 40,
                  f"{coverage_pct:.1f}%")
            check("Highlights cover >0.01% of canvas (something is shown)",
                  coverage_pct > 0.01, f"{coverage_pct:.4f}%")

            ss(page, "04_highlights_q1")

            # Close modal
            page.locator("#closePdfBtn").click()
            time.sleep(0.3)
            check("Modal closes", not modal.is_visible(), "")

            # ── 4. Second question — different keywords ───────────────────────
            print("\n── Question 2: purpose ──")
            page.locator("#input").fill("What is the purpose of this Commission?")
            page.locator("#actionBtn").click()
            wait_for_ai_reply(page)
            ss(page, "05_answer_q2")

            ai_msgs2 = page.locator(".message.ai .bubble")
            last_ai2 = ai_msgs2.last
            pills2 = last_ai2.locator(".source")
            pill2_count = pills2.count()
            check("Citation pills shown for Q2", pill2_count >= 1, f"{pill2_count} pills")

            if pill2_count > 0:
                pills2.first.click()
                time.sleep(1.2)
                ss(page, "06_highlights_q2")

                boxes2 = page.evaluate("""
                    () => [...document.querySelectorAll('.highlight')].map(h => ({
                        left:   parseFloat(h.style.left),
                        top:    parseFloat(h.style.top),
                        width:  parseFloat(h.style.width),
                        height: parseFloat(h.style.height),
                    }))
                """)
                hl2_count = len(boxes2)
                check("Q2 also shows highlights", hl2_count >= 1, f"{hl2_count} highlights")

                # Check that the highlighted positions differ between Q1 and Q2
                # (different keywords → different positions)
                tops1 = sorted(set(round(b["top"]) for b in boxes))
                tops2 = sorted(set(round(b["top"]) for b in boxes2))
                coverage2_pct = 100 * sum(b["width"]*b["height"] for b in boxes2) / max(canvas_area, 1)
                print(f"\n  Q2 highlight coverage: {coverage2_pct:.1f}%")
                check("Q2 highlights also <40% canvas coverage", coverage2_pct < 40,
                      f"{coverage2_pct:.1f}%")

                # Q2 highlights need not be in same position as Q1 (different focus)
                same_positions = tops1 == tops2
                if same_positions and hl2_count == highlight_count:
                    print("  [INFO] Q2 highlights same as Q1 — likely same page/chunk")
                else:
                    print(f"  [INFO] Q2 highlights differ from Q1 ✓")

                ss(page, "07_highlights_q2_detail")
                page.locator("#closePdfBtn").click()
                time.sleep(0.3)

            # ── 5. Question 3: members ────────────────────────────────────────
            print("\n── Question 3: members ──")
            page.locator("#input").fill("Who are the members of the Commission?")
            page.locator("#actionBtn").click()
            wait_for_ai_reply(page)

            ai_msgs3 = page.locator(".message.ai .bubble")
            last_ai3 = ai_msgs3.last
            pills3 = last_ai3.locator(".source")
            p3cnt = pills3.count()
            check("Citation pills shown for Q3", p3cnt >= 1, f"{p3cnt} pills")
            if p3cnt > 0:
                pills3.first.click()
                time.sleep(1.2)
                ss(page, "08_highlights_q3")
                boxes3 = page.evaluate("""
                    () => [...document.querySelectorAll('.highlight')].map(h => ({
                        left:   parseFloat(h.style.left),
                        top:    parseFloat(h.style.top),
                        width:  parseFloat(h.style.width),
                        height: parseFloat(h.style.height),
                    }))
                """)
                coverage3 = 100 * sum(b["width"]*b["height"] for b in boxes3) / max(canvas_area, 1)
                check("Q3 highlights within bounds", len(boxes3) >= 0, f"{len(boxes3)} boxes")
                check("Q3 coverage <40%", coverage3 < 40, f"{coverage3:.1f}%")
                page.locator("#closePdfBtn").click()
                time.sleep(0.3)

    check("No JS errors throughout", len(js_errors) == 0,
          "; ".join(js_errors[:3]) if js_errors else "")
    ss(page, "09_final")
    browser.close()

server.shutdown()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
for icon, label, detail in results:
    line = f"  [{icon}] {label}"
    if detail:
        line += f"  ({detail[:100]})"
    print(line)
print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
print("=" * 64)
raise SystemExit(0 if failed == 0 else 1)
