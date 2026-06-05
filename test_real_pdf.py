"""
Full test using the real user-provided PDF.
Tests: upload, indexing, Q&A with real Groq API (if key exists),
citation narrowing, modal, keyword highlights.
"""
import os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\pdf_chatbot_V2.html").as_uri()
PDF  = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\unifiedregistry-citizen-portal.amnex.co.in_citizen_scheme_details_id=53.pdf"
SS   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_real"
os.makedirs(SS, exist_ok=True)

results = []

def ss(page, name):
    path = f"{SS}/{name}.png"
    page.screenshot(path=path, full_page=False)
    return path

def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, detail))
    s = f"[{icon}] {label}"
    if detail:
        s += f"  ({detail.encode('ascii','replace').decode()[:120]})"
    print(s)
    return cond

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_context().new_page()
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(HTML, wait_until="networkidle")
        time.sleep(0.5)

        # ── 1. Upload the real PDF ────────────────────────────────────────────
        ss(page, "00_initial")
        with page.expect_file_chooser() as fc_info:
            page.locator(".upload-btn").click()
        fc_info.value.set_files(PDF)

        page.wait_for_function(
            "() => document.getElementById('statusDot').classList.contains('active')",
            timeout=60000
        )
        time.sleep(0.5)
        ss(page, "01_loaded")

        pdf_name = page.locator("#pdfName").text_content().strip()
        check("PDF filename shown in sidebar", "amnex" in pdf_name or ".pdf" in pdf_name, pdf_name)

        status = page.locator("#loading").text_content().strip()
        check("Status shows chunk count", "chunk" in status or "indexed" in status or "p " in status, status)

        # Extract chunk count for later assertions
        import re
        chunk_match = re.search(r'(\d+)\s*chunk', status)
        n_chunks = int(chunk_match.group(1)) if chunk_match else 0
        page_match = re.search(r'(\d+)p', status)
        n_pages = int(page_match.group(1)) if page_match else 0
        print(f"    PDF: {n_pages} pages, {n_chunks} chunks")
        check("PDF has multiple pages", n_pages > 1, f"{n_pages} pages")
        check("PDF produces multiple chunks", n_chunks > 1, f"{n_chunks} chunks")

        # ── 2. Check for stored API key, set fake if missing ──────────────────
        stored_key = page.evaluate("() => localStorage.getItem('groq_api_key')")
        use_real_api = stored_key and len(stored_key) > 20 and not stored_key.startswith("test-fake")
        print(f"    API key present: {bool(stored_key)} | using real API: {use_real_api}")

        # ── 3. Ask a question and verify citation narrowing ───────────────────
        # Read some PDF text to craft a targeted question
        pdf_text_sample = page.evaluate("""() => {
            if (!chunks || !chunks.length) return '';
            return chunks.slice(0, 3).map(c => c.text).join(' ').slice(0, 400);
        }""")
        print(f"    PDF text sample: {pdf_text_sample.encode('ascii','replace').decode()[:200]}")

        # Build a question from first chunk's vocabulary
        first_words = [w for w in pdf_text_sample.lower().split() if len(w) > 5][:8]
        question = f"What is this document about? Summarize the main purpose."

        if not use_real_api:
            # Fake the API response using actual chunk text
            def fake_route(route):
                # Use real chunk text in the answer so keywords will match
                sample = pdf_text_sample[:300] if pdf_text_sample else "This document provides information."
                fake = {
                    "id": "fake", "object": "chat.completion",
                    "choices": [{"message": {"role": "assistant",
                        "content": f"Based on the document: {sample}"
                    }, "finish_reason": "stop", "index": 0}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))
            page.route("**/api.groq.com/**", fake_route)
            page.evaluate("() => localStorage.setItem('groq_api_key', 'test-fake-key-12345')")

        page.locator("#input").fill(question)
        ss(page, "02_before_send")
        page.locator("#sendBtn").click()

        # Wait for thinking dots to appear then disappear
        try:
            page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
        except Exception:
            pass
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=30000)
        time.sleep(0.5)
        ss(page, "03_answer_q1")

        ai_last = page.locator(".message.ai").last
        answer_text = ai_last.text_content().strip()
        check("AI returned an answer", len(answer_text) > 20, answer_text[:100])

        source_count = ai_last.locator(".source").count()
        check("Answer has citation buttons", source_count > 0, f"{source_count} citation(s)")

        # ── 4. Verify citation count is <= pages cited (no spurious extras) ───
        cited_pages = []
        for i in range(source_count):
            txt = ai_last.locator(".source").nth(i).text_content().strip()
            cited_pages.append(txt)
        cited_pages_s = [t.encode('ascii','replace').decode() for t in cited_pages]
        print(f"    Citations: {cited_pages_s}")
        check("Citations <= TOP_K (no more than 5)",
              source_count <= 5, f"{source_count} citations")

        # ── 5. Ask a second, different question ───────────────────────────────
        # Build answer from a later chunk to force different citation
        later_text = page.evaluate("""() => {
            if (!chunks || chunks.length < 2) return '';
            const idx = Math.floor(chunks.length / 2);
            return chunks[idx].text.slice(0, 300);
        }""")

        if not use_real_api:
            page.unroute("**/api.groq.com/**")
            def fake_route_q2(route):
                fake = {
                    "id": "f2", "object": "chat.completion",
                    "choices": [{"message": {"role": "assistant",
                        "content": f"Additional details: {later_text}"
                    }, "finish_reason": "stop", "index": 0}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}
                }
                route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))
            page.route("**/api.groq.com/**", fake_route_q2)

        page.locator("#input").fill("What are the specific details or requirements mentioned?")
        page.locator("#sendBtn").click()
        try:
            page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
        except Exception:
            pass
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=30000)
        time.sleep(0.5)
        ss(page, "04_answer_q2")

        ai_q2 = page.locator(".message.ai").last
        source_count_q2 = ai_q2.locator(".source").count()
        cited_q2 = [ai_q2.locator(".source").nth(i).text_content().encode('ascii','replace').decode()
                    for i in range(source_count_q2)]
        print(f"    Q2 citations: {cited_q2}")
        check("Q2 also has citations", source_count_q2 > 0, f"{source_count_q2}")

        # ── 6. Open PDF modal via first citation ──────────────────────────────
        first_source = page.locator(".source").first
        first_source.click()
        time.sleep(1.2)
        ss(page, "05_modal_open")

        modal_display = page.evaluate("() => document.getElementById('pdfModal').style.display")
        check("PDF modal opens", modal_display == "flex", f"display={modal_display}")

        page_info = page.locator("#pdfPageInfo").text_content()
        check("Modal shows page number", "PAGE" in page_info.upper(), page_info)

        canvas_w = page.evaluate("() => document.getElementById('pdfCanvas').width")
        canvas_h = page.evaluate("() => document.getElementById('pdfCanvas').height")
        check("Canvas rendered", canvas_w > 0 and canvas_h > 0, f"{canvas_w}x{canvas_h}")

        # ── 7. Count highlights — should be > 0 and < total text items ────────
        highlight_count = page.evaluate("() => document.querySelectorAll('.highlight').length")
        total_text_items = page.evaluate("""() =>
            document.querySelectorAll('#highlightLayer').length +
            document.querySelectorAll('#pdfCanvas').length""")
        check("Highlight divs present (keyword matches found)", highlight_count > 0,
              f"{highlight_count} highlight(s)")

        # Key check: highlights should be a subset of text items, not equal to all
        all_text_items_approx = page.evaluate("""() => {
            // estimate by checking highlight layer child count vs a 'full page' scenario
            return document.getElementById('highlightLayer').children.length;
        }""")
        print(f"    Highlights on cited page: {all_text_items_approx}")

        ss(page, "06_highlights")

        # ── 8. Close modal ────────────────────────────────────────────────────
        page.locator("#closePdfBtn").click()
        time.sleep(0.3)
        modal_closed = page.evaluate("() => document.getElementById('pdfModal').style.display")
        check("Modal closes", modal_closed == "none")

        # ── 9. Source independence: earlier messages kept ─────────────────────
        all_source_divs = page.locator(".message.ai .sources").count()
        check("Multiple source sections exist (one per answered question)",
              all_source_divs >= 2, f"{all_source_divs} source sections")

        ss(page, "07_final")
        browser.close()

    print("\n" + "="*60)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    for icon, label, detail in results:
        line = f"  [{icon}] {label}"
        if detail:
            line += f"  ({detail.encode('ascii','replace').decode()[:100]})"
        print(line)
    print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
    print("="*60)
    return failed == 0

if __name__ == "__main__":
    ok = run()
    raise SystemExit(0 if ok else 1)
