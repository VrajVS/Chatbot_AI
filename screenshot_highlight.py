"""Screenshot the keyword-highlight modal to visually confirm narrowing."""
import os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\pdf_chatbot_V2.html").as_uri()
PDF  = str(Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"))
SS   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots"

def route_q1(route):
    fake = {"id":"x","object":"chat.completion","choices":[{"message":{"role":"assistant",
        "content":"The introduction describes neural networks as computational models. Deep learning uses multiple layers to learn representations from data."},
        "finish_reason":"stop","index":0}],"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}
    route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=80)
    page = browser.new_page()
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto(HTML, wait_until="networkidle")

    with page.expect_file_chooser() as fc:
        page.locator(".upload-btn").click()
    fc.value.set_files(PDF)
    page.wait_for_function("() => document.getElementById('statusDot').classList.contains('active')", timeout=15000)
    time.sleep(0.3)

    page.route("**/api.groq.com/**", route_q1)
    page.evaluate("() => localStorage.setItem('groq_api_key', 'test-fake-key')")
    page.locator("#input").fill("What is the introduction about?")
    page.locator("#sendBtn").click()
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
    time.sleep(0.4)

    # Inspect keywords that were computed
    keywords = page.evaluate("""() => {
        const btns = document.querySelectorAll('.source');
        if (!btns.length) return null;
        // The keywords are stored in the closure — re-derive from visible text
        return btns[0].textContent;
    }""")
    print(f"Source button: {keywords.encode('ascii','replace').decode() if keywords else None}")

    # Click citation to open modal
    page.locator(".source").first.click()
    time.sleep(1.0)

    highlight_count = page.evaluate("() => document.querySelectorAll('.highlight').length")
    print(f"Highlight divs on page: {highlight_count}")

    page.screenshot(path=f"{SS}/highlight_keywords.png")
    print(f"Screenshot saved.")
    time.sleep(1.0)
    browser.close()
