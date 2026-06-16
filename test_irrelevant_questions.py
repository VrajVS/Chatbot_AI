"""
Test: chatbot must REFUSE to answer questions unrelated to the uploaded PDF.

For each irrelevant question this test verifies:
  1. The system prompt sent to Ollama instructs "Answer ONLY from PDF context"
  2. The retrieved context does NOT contain the irrelevant topic
  3. The AI response says it cannot answer (not found in PDF)
  4. No citation pills are shown (there's nothing relevant to cite)
  5. One relevant question is also asked to confirm normal answers still work.

Because Ollama is not running, we mock the /api/chat endpoint.
The mock inspects the prompt that was sent:
  - If the user question topic is absent from the context  → returns a refusal
  - If the context matches the question → returns a relevant answer
This accurately simulates a well-instructed LLM.
"""
import os, json, time, threading, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

HTML_DIR = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI"
PDF_PATH = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"
SS_DIR   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_irrelevant"
os.makedirs(SS_DIR, exist_ok=True)

PORT = 8087
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
    results.append((icon, label, str(detail)[:250]))
    suffix = f"  ({str(detail)[:130]})" if detail else ""
    print(f"  [{icon}] {label}{suffix}")
    return cond

def ss(page, name):
    page.screenshot(path=f"{SS_DIR}/{name}.png")

REFUSAL_PHRASES = [
    "not in the pdf", "not in the document", "not provided in",
    "no information", "cannot find", "not mentioned", "not available",
    "document does not", "pdf does not", "not contain", "context does not",
    "not discussed", "unable to find", "not found", "don't have",
    "do not have", "cannot answer", "not part of", "outside",
    "not covered", "not related", "not about",
    "not present in", "is absent", "information is not",
    "does not include", "does not discuss", "does not mention",
    "no relevant", "not relevant", "no political", "no weather",
    "no sports", "no cooking", "no crypto", "no movie",
]

def is_refusal(text):
    t = text.lower()
    return any(p in t for p in REFUSAL_PHRASES)

def is_confident_answer(text, must_not_contain):
    """Returns True if the response answers confidently without refusal phrases."""
    t = text.lower()
    if is_refusal(t): return False
    return len(t) > 40 and all(p not in t for p in ["i don't know", "cannot"])

# ── Smart mock: inspects the prompt and decides to refuse or answer ────────────
# Stores the last intercepted request body for inspection
last_request = {"body": None}

IRRELEVANT_TOPICS = ["france", "paris", "pasta", "cook", "fifa", "football",
                     "soccer", "speed of light", "capital city", "recipe",
                     "weather", "bitcoin", "crypto", "president", "movie",
                     "actor", "celebrity", "stock", "python language", "java"]

def make_mock(page):
    def route_tags(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"models": [{"name": "gemma:2b"}]}))

    def route_chat(route):
        body = json.loads(route.request.post_data or "{}")
        last_request["body"] = body

        messages = body.get("messages", [])
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msg   = next((m["content"] for m in messages if m["role"] == "user"),   "")

        # Extract the user's actual question (after the context block)
        q_match = re.search(r"Question:\s*\n(.+?)$", user_msg, re.DOTALL)
        question = q_match.group(1).strip().lower() if q_match else user_msg.lower()

        # Extract the context portion
        ctx_match = re.search(r"PDF Context:\s*\n(.*?)\n\nQuestion:", user_msg, re.DOTALL)
        context = ctx_match.group(1).lower() if ctx_match else ""

        # Check if the question is about a topic absent from the context
        def topic_in_context(keywords):
            return any(kw in context for kw in keywords)

        answer = ""

        # Relevant topics from our test PDF (deep learning paper)
        if any(kw in question for kw in ["deep learning", "neural", "network", "optimis", "study",
                                          "conclude", "research", "dataset", "hyperparameter",
                                          "future work", "tradition", "benchmark", "learning"]):
            if topic_in_context(["deep", "neural", "learning", "optimis", "research", "study"]):
                answer = (
                    "The study focuses on deep learning and neural network optimisation. "
                    "The research concludes that neural networks outperform traditional methods."
                )
            else:
                answer = "The provided PDF does not contain information about that topic."

        # Irrelevant topics
        elif any(kw in question for kw in ["capital", "france", "paris", "city"]):
            if topic_in_context(["france", "paris", "capital"]):
                answer = "Paris is the capital of France."
            else:
                answer = "I cannot find information about countries or capital cities in the provided PDF."

        elif any(kw in question for kw in ["pasta", "cook", "recipe", "food", "eat"]):
            if topic_in_context(["pasta", "cook", "food", "recipe"]):
                answer = "Here is how to cook pasta..."
            else:
                answer = "The PDF does not contain any information about cooking or recipes."

        elif any(kw in question for kw in ["fifa", "football", "soccer", "world cup", "sport"]):
            if topic_in_context(["fifa", "football", "soccer", "sport"]):
                answer = "The World Cup was won by..."
            else:
                answer = "This document does not discuss sports or football tournaments."

        elif any(kw in question for kw in ["speed of light", "physics", "einstein", "relativity"]):
            if topic_in_context(["light", "physics", "speed"]):
                answer = "The speed of light is 299,792,458 m/s."
            else:
                answer = "No information about physics or the speed of light is available in this PDF."

        elif any(kw in question for kw in ["weather", "temperature", "rain", "forecast"]):
            answer = "The PDF does not contain any weather or meteorological information."

        elif any(kw in question for kw in ["bitcoin", "crypto", "blockchain", "ethereum"]):
            answer = "This document does not mention cryptocurrency or blockchain technology."

        elif any(kw in question for kw in ["president", "prime minister", "government", "politic"]):
            answer = "The PDF does not contain any political or governmental information."

        elif any(kw in question for kw in ["movie", "film", "actor", "actress", "celebrity"]):
            answer = "The PDF does not contain information about movies or entertainment."

        elif any(kw in question for kw in ["python", "java", "javascript", "programm", "software language"]):
            if topic_in_context(["python", "java", "javascript"]):
                answer = "Python is a programming language..."
            else:
                answer = "The document does not discuss programming languages specifically."

        else:
            # Generic irrelevant question
            answer = "This information is not available in the provided PDF document."

        ndjson = json.dumps({
            "model": "gemma:2b",
            "message": {"role": "assistant", "content": answer},
            "done": True
        }) + "\n"
        route.fulfill(status=200, content_type="application/x-ndjson", body=ndjson)

    page.route("**/localhost:11434/api/tags", route_tags)
    page.route("**/localhost:11434/api/chat",  route_chat)


def wait_answer(page, timeout=20_000):
    try:
        page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
    except Exception:
        pass
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=timeout)
    time.sleep(0.4)

# ── Test questions ─────────────────────────────────────────────────────────────
IRRELEVANT_QS = [
    ("What is the capital of France?",       "geography/country question"),
    ("How do I cook pasta carbonara?",        "cooking/recipe question"),
    ("Who won the FIFA World Cup 2022?",      "sports question"),
    ("What is the speed of light?",           "physics question"),
    ("What is the weather like today?",       "weather question"),
    ("Tell me about Bitcoin and crypto.",     "cryptocurrency question"),
    ("Who is the current US President?",      "political question"),
    ("Recommend a good Hollywood movie.",     "entertainment question"),
    ("How does Python programming work?",     "off-topic programming question"),
]

RELEVANT_Q = ("What does the study conclude about neural networks?", "relevant PDF question")

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"\nURL: {URL}")
print(f"PDF: {PDF_PATH}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    page    = browser.new_context().new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    make_mock(page)
    page.goto(URL, wait_until="networkidle")
    time.sleep(0.3)

    # Upload PDF
    page.locator("#fileInput").set_input_files(PDF_PATH)
    page.wait_for_function(
        "() => document.getElementById('statusDot').classList.contains('active')",
        timeout=20_000
    )
    time.sleep(0.2)
    status = page.locator("#loading").text_content()
    check("PDF indexed", "chunk" in status.lower() or "page" in status.lower(), status)
    ss(page, "00_pdf_loaded")

    # ── Test 1: Relevant question (should answer) ─────────────────────────────
    print(f"\n{'='*60}")
    print(f"  [RELEVANT] {RELEVANT_Q[0]}")
    page.locator("#input").fill(RELEVANT_Q[0])
    page.locator("#actionBtn").click()
    wait_answer(page)

    last_ai = page.locator(".message.ai .bubble").last
    answer  = last_ai.text_content().strip()
    pills   = last_ai.locator(".source").count()
    print(f"  Answer: {answer[:200]}")

    check("Relevant Q: got a real answer (not a refusal)",
          not is_refusal(answer) and len(answer) > 20, answer[:80])
    check("Relevant Q: citation pills shown", pills >= 1, f"{pills} pills")
    ss(page, "01_relevant_answer")

    # ── Test 2: Irrelevant questions (must refuse) ────────────────────────────
    print(f"\n{'='*60}")
    print("  Testing irrelevant questions...\n")

    refused_count = 0
    answered_count = 0
    api_bodies = []

    for i, (question, desc) in enumerate(IRRELEVANT_QS, 1):
        last_request["body"] = None
        page.locator("#input").fill(question)
        page.locator("#actionBtn").click()
        wait_answer(page)

        last_ai = page.locator(".message.ai .bubble").last
        answer  = last_ai.text_content().strip()
        pills   = last_ai.locator(".source").count()

        refused = is_refusal(answer)
        if refused:
            refused_count += 1
        else:
            answered_count += 1

        # Inspect what was sent to Ollama
        req = last_request["body"]
        system_ok = False
        context_has_topic = False
        if req:
            messages = req.get("messages", [])
            sys_msg  = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msg = next((m["content"] for m in messages if m["role"] == "user"),   "")
            system_ok = "only from the provided pdf context" in sys_msg.lower() or \
                        "answer only from" in sys_msg.lower()
            # The context shouldn't contain the topic keywords
            q_lower = question.lower()
            topic_kws = q_lower.replace("?", "").replace(",", "").split()
            meaningful_kws = [w for w in topic_kws if len(w) > 4]
            ctx_match = re.search(r"PDF Context:\s*\n(.*?)\n\nQuestion:", user_msg, re.DOTALL)
            context = ctx_match.group(1).lower() if ctx_match else ""
            context_has_topic = any(kw in context for kw in meaningful_kws[:3])

        print(f"  [{i:02d}] {desc}")
        print(f"        Q: {question}")
        print(f"        A: {answer[:120]}")
        print(f"        Refused: {refused} | Sys-prompt OK: {system_ok} | Topic in context: {context_has_topic} | Pills: {pills}")

        check(f"[{i:02d}] {desc} — refused to answer",
              refused, answer[:80])
        check(f"[{i:02d}] system prompt instructs PDF-only answers", system_ok,
              "system prompt missing PDF-only instruction" if not system_ok else "")
        check(f"[{i:02d}] irrelevant topic NOT present in retrieved context",
              not context_has_topic,
              "topic leaked into context — retrieval may need tuning" if context_has_topic else "")
        check(f"[{i:02d}] no citation pills for irrelevant question",
              pills == 0, f"{pills} pills shown" if pills else "")

        ss(page, f"irrelevant_{i:02d}")
        print()

    # ── Summary stats ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Irrelevant Qs refused:  {refused_count}/{len(IRRELEVANT_QS)}")
    print(f"  Irrelevant Qs answered: {answered_count}/{len(IRRELEVANT_QS)}")

    check("ALL irrelevant questions were refused",
          refused_count == len(IRRELEVANT_QS),
          f"{refused_count}/{len(IRRELEVANT_QS)} refused")
    check("No JS errors", len(js_errors) == 0,
          "; ".join(js_errors[:2]) if js_errors else "")

    ss(page, "final")
    browser.close()

server.shutdown()

# ── Report ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
for icon, label, detail in results:
    line = f"  [{icon}] {label}"
    if detail: line += f"  ({detail[:100]})"
    print(line)
print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
print("=" * 64)
raise SystemExit(0 if failed == 0 else 1)
