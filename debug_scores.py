"""Minimal debug script: upload PDF, send Q1, inspect citation scores."""
import os, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI\pdf_chatbot_V2.html").as_uri()
PDF  = str(Path(r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"))

def handle_route(route):
    fake = {
        "id": "fake", "object": "chat.completion",
        "choices": [{"message": {"role": "assistant",
            "content": "The introduction describes neural networks as computational models. Deep learning uses multiple layers to learn representations from data."
        }, "finish_reason": "stop", "index": 0}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    }
    route.fulfill(status=200, content_type="application/json", body=json.dumps(fake))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(HTML, wait_until="networkidle")

    # Upload PDF
    with page.expect_file_chooser() as fc_info:
        page.locator(".upload-btn").click()
    fc_info.value.set_files(PDF)
    page.wait_for_function(
        "() => document.getElementById('statusDot').classList.contains('active')",
        timeout=15000
    )
    time.sleep(0.3)

    # Inspect IDF
    idf_size = page.evaluate("() => Object.keys(idf).length")
    idf_sample = page.evaluate("() => { const e = {}; Object.keys(idf).slice(0,10).forEach(k => e[k]=idf[k]); return e; }")
    print(f"\nidf size: {idf_size}")
    print(f"idf sample: {json.dumps(idf_sample, indent=2)}")

    # Send question
    page.route("**/api.groq.com/**", handle_route)
    page.evaluate("() => localStorage.setItem('groq_api_key', 'test-fake-key')")
    page.locator("#input").fill("What is the introduction about?")
    page.locator("#sendBtn").click()
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=10000)
    time.sleep(0.3)

    scores = page.evaluate("() => window.__lastCitationScores")
    idf_at_query = page.evaluate("() => window.__lastIdfSize")
    top_score = page.evaluate("() => window.__lastTopScore")

    print(f"\nIDF size at query time: {idf_at_query}")
    print(f"Top score: {top_score}")
    print(f"Citation scores by page: {scores}")
    print(f"  ratio p2/p1: {scores[1]['score']/scores[0]['score'] if scores and scores[0]['score']>0 else 'N/A':.3f}")
    print(f"  ratio p3/p1: {scores[2]['score']/scores[0]['score'] if len(scores)>2 and scores[0]['score']>0 else 'N/A':.3f}")

    browser.close()
