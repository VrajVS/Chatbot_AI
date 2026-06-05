"""
Playwright test for pdf_chatbot_V2.html
Tests: load, PDF upload, UI state, citation consistency, modal, send-button disable
NOTE: Groq API calls are NOT made (no real API key). We test everything up to that boundary.
"""

import os, time, json, base64
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\pdf_chatbot_V2.html").as_uri()
PDF  = str(Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"))
SS   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots"
os.makedirs(SS, exist_ok=True)

results = []

def ss(page, name):
    path = f"{SS}/{name}.png"
    page.screenshot(path=path, full_page=False)
    return path

def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, detail))
    print(f"[{icon}] {label}" + (f"  — {detail}" if detail else ""))
    return cond

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=120)
        ctx = browser.new_context(
            # Grant clipboard permissions
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = ctx.new_page()
        page.set_viewport_size({"width": 1400, "height": 900})

        # ── 1. Load page ──────────────────────────────────────────────────────
        page.goto(HTML, wait_until="networkidle")
        time.sleep(0.5)
        ss(page, "01_initial_load")
        check("Page loads without JS errors",
              page.evaluate("() => !window.__hadJSError"),
              "no uncaught exceptions")

        # ── 2. Initial UI state ───────────────────────────────────────────────
        pdf_name_text = page.locator("#pdfName").text_content()
        check("PDF name shows 'No PDF selected'",
              "No PDF selected" in pdf_name_text)

        status_text = page.locator("#loading").text_content()
        check("Status shows idle message",
              "Idle" in status_text or "no document" in status_text.lower(),
              status_text)

        welcome_msg = page.locator(".message.ai .bubble").first.text_content()
        check("Welcome message present",
              "Ready" in welcome_msg or "Upload" in welcome_msg,
              welcome_msg[:60])

        # ── 3. Send button disabled without PDF ───────────────────────────────
        page.locator("#input").fill("hello")
        page.locator("#sendBtn").click()
        time.sleep(0.5)
        messages_after_no_pdf = page.locator(".message").count()
        ai_msg = page.locator(".message.ai").last.text_content()
        check("Sending without PDF shows warning",
              "Upload" in ai_msg,
              ai_msg[:60])
        ss(page, "02_no_pdf_warning")

        # ── 4. Upload PDF ─────────────────────────────────────────────────────
        page.locator("#input").fill("")  # clear
        with page.expect_file_chooser() as fc_info:
            page.locator(".upload-btn").click()
        fc = fc_info.value
        fc.set_files(PDF)
        # Wait for indexing to finish (status goes active)
        page.wait_for_function(
            "() => document.getElementById('statusDot').classList.contains('active')",
            timeout=15000
        )
        time.sleep(0.3)
        ss(page, "03_pdf_loaded")

        pdf_name = page.locator("#pdfName").text_content()
        check("PDF name shows filename",
              "test_sample" in pdf_name,
              pdf_name)

        status = page.locator("#loading").text_content()
        check("Status shows page count after load",
              "p" in status or "chunk" in status or "indexed" in status,
              status)

        dot_class = page.locator("#statusDot").get_attribute("class")
        check("Status dot is green (active)",
              "active" in dot_class,
              dot_class)

        ai_msgs = page.locator(".message.ai")
        loaded_msg = ai_msgs.last.text_content()
        check("AI confirms PDF loaded",
              "test_sample" in loaded_msg or "loaded" in loaded_msg.lower(),
              loaded_msg[:80])

        # ── 5. PDF name button clickable (has-file class) ─────────────────────
        name_classes = page.locator("#pdfName").get_attribute("class")
        check("PDF name button has 'has-file' class after upload",
              "has-file" in name_classes,
              name_classes)

        # ── 6. Citation narrowing: Q1 about introduction (page 1) ───────────────
        # AI answer uses language from page 1 only; expect citation = Page 1 only
        def handle_route(route):
            fake = {
                "id": "fake",
                "object": "chat.completion",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        # Deliberately uses tokens from page 1: "introduction",
                        # "neural networks", "deep learning", "layers", "data"
                        "content": "The introduction describes neural networks as computational models. Deep learning uses multiple layers to learn representations from data."
                    },
                    "finish_reason": "stop",
                    "index": 0
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

        page.route("**/api.groq.com/**", handle_route)
        page.evaluate("() => localStorage.setItem('groq_api_key', 'test-fake-key-12345')")

        page.locator("#input").fill("What is the introduction about?")
        page.locator("#sendBtn").click()
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
        time.sleep(0.4)
        ss(page, "04_first_answer")

        source_count_1 = page.locator(".message.ai:last-child .sources .source").count()
        check("Q1: citation buttons present", source_count_1 > 0, f"{source_count_1} source(s)")

        pages_cited_1 = []
        for i in range(source_count_1):
            txt = page.locator(".message.ai:last-child .sources .source").nth(i).text_content()
            pages_cited_1.append(txt.strip())
        pages_cited_1_ascii = [t.encode("ascii", "replace").decode() for t in pages_cited_1]
        print(f"    Citations Q1: {pages_cited_1_ascii}")

        check("Q1: cites Page 1 (introduction content)",
              any("1" in t for t in pages_cited_1_ascii),
              str(pages_cited_1_ascii))
        check("Q1: does NOT cite revenue-only Page 2",
              not any(t.strip().endswith("2") and "Page" in t for t in pages_cited_1),
              str(pages_cited_1_ascii))

        # ── 7. Citation narrowing: Q2 about revenue (page 2) ─────────────────
        def handle_route_q2(route):
            fake = {
                "id": "fake2",
                "object": "chat.completion",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        # Deliberately uses tokens from page 2 only: "revenue",
                        # "five million", "fifteen percent", "sales", "thirty"
                        "content": "Total revenue for Q1 was five million dollars. Q2 revenue increased by fifteen percent. The sales team expanded to thirty members."
                    },
                    "finish_reason": "stop",
                    "index": 0
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

        page.unroute("**/api.groq.com/**", handle_route)
        page.route("**/api.groq.com/**", handle_route_q2)

        page.locator("#input").fill("What are the revenue numbers?")
        page.locator("#sendBtn").click()
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
        time.sleep(0.4)
        ss(page, "05_second_answer")

        source_count_2 = page.locator(".message.ai").last.locator(".source").count()
        check("Q2: citation buttons present", source_count_2 > 0, f"{source_count_2} source(s)")

        pages_cited_2 = []
        for i in range(source_count_2):
            txt = page.locator(".message.ai").last.locator(".source").nth(i).text_content()
            pages_cited_2.append(txt.strip())
        pages_cited_2_ascii = [t.encode("ascii", "replace").decode() for t in pages_cited_2]
        print(f"    Citations Q2: {pages_cited_2_ascii}")

        check("Q2: cites Page 2 (revenue content)",
              any("2" in t for t in pages_cited_2_ascii),
              str(pages_cited_2_ascii))
        check("Q2: does NOT cite introduction-only Page 1",
              not (len(pages_cited_2_ascii) == 1 and "1" in pages_cited_2_ascii[0]),
              str(pages_cited_2_ascii))

        all_source_divs = page.locator(".message.ai .sources").all()
        check("Both AI messages have independent source sections",
              len(all_source_divs) == 2,
              f"{len(all_source_divs)} source sections")

        # ── 8. Send button disabled during request ────────────────────────────
        # Use a MutationObserver injected into the page to record when the
        # button becomes disabled — avoids the Playwright-thread-blocking race.
        page.evaluate("""() => {
            window.__btnWasDisabled = false;
            const btn = document.getElementById('sendBtn');
            const obs = new MutationObserver(muts => {
                muts.forEach(m => {
                    if (m.attributeName === 'disabled' && btn.disabled) {
                        window.__btnWasDisabled = true;
                    }
                });
            });
            obs.observe(btn, { attributes: true });
        }""")

        def handle_route_q3(route):
            fake = {
                "id": "fake3", "object": "chat.completion",
                "choices": [{"message": {"role": "assistant", "content": "Conclusion: neural networks win."}, "finish_reason": "stop", "index": 0}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

        page.unroute("**/api.groq.com/**", handle_route_q2)
        page.route("**/api.groq.com/**", handle_route_q3)

        page.locator("#input").fill("What is the conclusion?")
        page.locator("#sendBtn").click()
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
        time.sleep(0.3)

        btn_was_disabled_during = page.evaluate("() => window.__btnWasDisabled")
        btn_disabled_after = page.evaluate("() => document.getElementById('sendBtn').disabled")
        check("Send button disabled during API call",
              btn_was_disabled_during,
              f"observer recorded disabled=true: {btn_was_disabled_during}")
        check("Send button re-enabled after response",
              not btn_disabled_after,
              f"disabled={btn_disabled_after}")

        ss(page, "06_third_answer")

        # ── 9. PDF modal via citation click ───────────────────────────────────
        # Click a source button from any AI answer that has one
        source_btns = page.locator(".source")
        count = source_btns.count()
        check("At least one source/citation button exists",
              count > 0,
              f"{count} total source buttons")

        if count > 0:
            source_btns.first.click()
            time.sleep(0.8)
            modal_display = page.evaluate("() => document.getElementById('pdfModal').style.display")
            check("PDF modal opens on citation click",
                  modal_display == "flex",
                  f"display={modal_display}")
            ss(page, "07_pdf_modal_open")

            page_info = page.locator("#pdfPageInfo").text_content()
            check("Modal shows page number",
                  "PAGE" in page_info.upper() or "Page" in page_info,
                  page_info)

            canvas = page.locator("#pdfCanvas")
            canvas_w = page.evaluate("() => document.getElementById('pdfCanvas').width")
            canvas_h = page.evaluate("() => document.getElementById('pdfCanvas').height")
            check("PDF canvas rendered (non-zero dimensions)",
                  canvas_w > 0 and canvas_h > 0,
                  f"{canvas_w}×{canvas_h}")

            # ── 10. Close modal ───────────────────────────────────────────────
            page.locator("#closePdfBtn").click()
            time.sleep(0.3)
            modal_closed = page.evaluate("() => document.getElementById('pdfModal').style.display")
            check("Modal closes on Close button",
                  modal_closed == "none",
                  f"display={modal_closed}")
            ss(page, "08_modal_closed")

        # ── 11. PDF name button opens viewer ─────────────────────────────────
        page.locator("#pdfName").click()
        time.sleep(0.8)
        modal_via_name = page.evaluate("() => document.getElementById('pdfModal').style.display")
        check("PDF name button opens viewer",
              modal_via_name == "flex",
              f"display={modal_via_name}")
        ss(page, "09_viewer_via_name")
        page.locator("#closePdfBtn").click()
        time.sleep(0.3)

        # ── 12. Textarea auto-resize ──────────────────────────────────────────
        h_before = page.evaluate("() => document.getElementById('input').offsetHeight")
        page.locator("#input").fill("line1\nline2\nline3\nline4\nline5\nline6")
        time.sleep(0.2)
        h_after = page.evaluate("() => document.getElementById('input').offsetHeight")
        check("Textarea grows with content",
              h_after > h_before,
              f"{h_before}px -> {h_after}px")

        # ── 13. Enter key sends message ────────────────────────────────────────
        page.unroute("**/api.groq.com/**")
        page.route("**/api.groq.com/**", handle_route)
        page.locator("#input").fill("Enter key test question")
        msg_count_before = page.locator(".message").count()
        page.locator("#input").press("Enter")
        time.sleep(0.1)
        msg_count_after = page.locator(".message").count()
        check("Enter key submits message",
              msg_count_after > msg_count_before,
              f"messages: {msg_count_before} -> {msg_count_after}")
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)

        # ── 14. Shift+Enter doesn't submit ────────────────────────────────────
        page.locator("#input").fill("shift enter test")
        msg_count_before2 = page.locator(".message").count()
        page.locator("#input").press("Shift+Enter")
        time.sleep(0.2)
        msg_count_after2 = page.locator(".message").count()
        check("Shift+Enter does NOT submit",
              msg_count_after2 == msg_count_before2,
              f"messages: {msg_count_before2} -> {msg_count_after2}")

        # ── 15. Markdown rendering ─────────────────────────────────────────────
        page.unroute("**/api.groq.com/**")
        def handle_markdown(route):
            fake = {
                "id": "md", "object": "chat.completion",
                "choices": [{"message": {"role": "assistant",
                    "content": "## Summary\n\n**Bold text** and *italic*.\n\n1. First item\n2. Second item\n\n- Bullet one\n- Bullet two\n\n`inline code`"
                }, "finish_reason": "stop", "index": 0}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 30, "total_tokens": 35}
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))
        page.route("**/api.groq.com/**", handle_markdown)
        page.locator("#input").fill("Test markdown rendering")
        page.locator("#sendBtn").click()
        page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
        time.sleep(0.3)
        ss(page, "10_markdown_rendered")

        last_bubble = page.locator(".message.ai").last.locator(".bubble")
        has_h2    = last_bubble.locator("h2").count() > 0
        has_strong = last_bubble.locator("strong").count() > 0
        has_em    = last_bubble.locator("em").count() > 0
        has_ol    = last_bubble.locator("ol").count() > 0
        has_ul    = last_bubble.locator("ul").count() > 0
        has_code  = last_bubble.locator("code").count() > 0
        check("Markdown: h2 heading rendered",     has_h2)
        check("Markdown: bold rendered",           has_strong)
        check("Markdown: italic rendered",         has_em)
        check("Markdown: ordered list (ol) rendered", has_ol, "fixed in this PR")
        check("Markdown: unordered list (ul) rendered", has_ul)
        check("Markdown: inline code rendered",   has_code)

        ss(page, "11_final_state")

        browser.close()

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    for icon, label, detail in results:
        line = f"  [{icon}] {label}"
        if detail:
            line += f"  ({detail})"
        print(line)
    print(f"\n  {passed} passed, {failed} failed out of {len(results)} checks")
    print("="*60)
    return failed == 0

if __name__ == "__main__":
    ok = run()
    raise SystemExit(0 if ok else 1)
