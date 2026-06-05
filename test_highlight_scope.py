"""
Visual test: confirm highlights are scoped to the chunk region, not the whole page.
Asks a targeted question about 'applicant type' and captures before/after screenshots
showing only the relevant section highlighted.
"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\pdf_chatbot_V2.html").as_uri()
PDF  = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\unifiedregistry-citizen-portal.amnex.co.in_citizen_scheme_details_id=53.pdf"
SS   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_scope"
import os; os.makedirs(SS, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=80)
    page = browser.new_context().new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(HTML, wait_until="networkidle")

    # Upload PDF
    with page.expect_file_chooser() as fc:
        page.locator(".upload-btn").click()
    fc.value.set_files(PDF)
    page.wait_for_function(
        "() => document.getElementById('statusDot').classList.contains('active')",
        timeout=60000
    )
    time.sleep(0.5)

    # Pull actual chunk text so we can see what's in each chunk
    chunk_info = page.evaluate("""() => chunks.map((c, i) => ({
        i, page: c.page, len: c.text.length,
        preview: c.text.slice(0, 120).replace(/\\s+/g,' ')
    }))""")
    print("\nChunks:")
    for c in chunk_info:
        print(f"  [{c['i']}] page={c['page']} len={c['len']} | {c['preview'].encode('ascii','replace').decode()}")

    # Ask specifically about applicant type — this keyword appears repeatedly in the PDF
    # Use a fake API response that mentions 'applicant' so the keyword scoring picks it up
    def fake_route(route):
        fake = {
            "id": "x", "object": "chat.completion",
            "choices": [{"message": {"role": "assistant",
                "content": "The document shows the applicant type is Individual Applicant. The applicant profile also includes annual family income and contact classification details."
            }, "finish_reason": "stop", "index": 0}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 30, "total_tokens": 40}
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

    page.route("**/api.groq.com/**", fake_route)
    page.evaluate("() => localStorage.setItem('groq_api_key', 'test-fake-key-12345')")
    page.locator("#input").fill("What is the applicant type and applicant profile?")
    page.locator("#sendBtn").click()

    try:
        page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
    except Exception:
        pass
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=15000)
    time.sleep(0.5)

    # Capture citation info
    ai_last = page.locator(".message.ai").last
    sources = ai_last.locator(".source").all()
    print(f"\nCitations: {[s.text_content().encode('ascii','replace').decode() for s in sources]}")

    page.screenshot(path=f"{SS}/01_answer.png", full_page=False)

    # Open the first citation
    page.locator(".source").first.click()
    time.sleep(1.5)
    page.screenshot(path=f"{SS}/02_modal_open.png", full_page=False)

    # Count and report highlights
    highlights = page.evaluate("() => document.querySelectorAll('.highlight').length")
    print(f"\nHighlight divs: {highlights}")

    # Get bounding boxes of all highlights to confirm they're in a narrow region
    boxes = page.evaluate("""() => Array.from(document.querySelectorAll('.highlight')).map(d => ({
        top: parseFloat(d.style.top),
        left: parseFloat(d.style.left),
        w: parseFloat(d.style.width),
        h: parseFloat(d.style.height)
    }))""")
    if boxes:
        tops = [b['top'] for b in boxes]
        print(f"  Highlight Y range: {min(tops):.0f}px — {max(tops):.0f}px  (spread: {max(tops)-min(tops):.0f}px)")
        print(f"  Canvas height: {page.evaluate('() => document.getElementById(\"pdfCanvas\").height')}px")
        print(f"  Boxes: {[round(b['top']) for b in boxes]}")

    page.screenshot(path=f"{SS}/03_highlights_zoomed.png", full_page=False)

    # Close modal
    page.locator("#closePdfBtn").click()
    time.sleep(0.3)

    browser.close()

print(f"\nScreenshots saved to {SS}")
