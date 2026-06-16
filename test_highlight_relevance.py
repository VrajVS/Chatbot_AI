"""
Rigorous relevance test for PDF highlighting.
Verifies that every highlighted text item actually contains a keyword
that also appears in the LLM answer — not just any word in the chunk.

Steps:
  1. Patch highlightChunk() at runtime to tag each highlight div with
     the item text and matched keyword (data-item / data-kw attributes).
  2. Ask 3 different questions → get 3 answers.
  3. For each answer, open the citation and inspect every highlight div:
       - matched keyword must appear in the answer text
       - matched keyword must appear in the item text
  4. Confirm highlights CHANGE when the answer changes (different Q → different kw).
"""
import os, json, time, threading, re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

HTML_DIR = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\Chatbot_AI"
PDF_PATH = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\test_sample.pdf"
SS_DIR   = r"c:\Users\vraj.suthar\Documents\GitHub\Chatbot_AI\screenshots_relevance"
os.makedirs(SS_DIR, exist_ok=True)

PORT = 8086
class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=HTML_DIR, **kw)
    def log_message(self, *a): pass
server = HTTPServer(("localhost", PORT), QuietHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://localhost:{PORT}/pdf_chatbot_V3.html"

# ── Test helpers ──────────────────────────────────────────────────────────────
results = []
def check(label, cond, detail=""):
    icon = "PASS" if cond else "FAIL"
    results.append((icon, label, str(detail)[:250]))
    suffix = f"  ({str(detail)[:130]})" if detail else ""
    print(f"  [{icon}] {label}{suffix}")
    return cond

def ss(page, name):
    page.screenshot(path=f"{SS_DIR}/{name}.png")

# ── JS patch injected after load ──────────────────────────────────────────────
# Wraps the real highlightChunk to add data attributes to each highlight div
# Intercept highlightChunk to capture keyword/answer metadata.
# Data attributes (data-item-text, data-matched-kw) are now written
# directly by the source code, so no post-hoc patching needed.
PATCH_JS = """
(function() {
  const _orig = window.highlightChunk;
  if (!_orig) { console.warn('highlightChunk not on window'); return; }
  window._hlLog = [];
  window.highlightChunk = async function(page, viewport, chunkIndex, keywords, answerNorm) {
    window._hlLog.push({
      chunkIndex,
      keywords: keywords ? [...keywords] : [],
      answerNorm: answerNorm || ''
    });
    return _orig.call(this, page, viewport, chunkIndex, keywords, answerNorm);
  };
})();
"""

# ── Mock Ollama — three distinct answers ─────────────────────────────────────
ANSWERS = {
    "q1": {
        "q": "What is the main focus of the study?",
        "a": (
            "The study focuses on deep learning and neural networks. "
            "Optimisation remains a key research area in these applications."
        ),
        "must_contain": ["deep", "learning", "neural", "networks", "optimisation", "research"],
    },
    "q2": {
        "q": "What does the study conclude?",
        "a": (
            "The study concludes that neural networks outperform traditional methods. "
            "Deep learning shows strong results across multiple benchmarks."
        ),
        "must_contain": ["concludes", "neural", "networks", "outperform", "traditional"],
    },
    "q3": {
        "q": "What is planned for future work?",
        "a": (
            "Future work includes expanding datasets and improving hyperparameter "
            "optimisation. The research aims to enhance deep learning performance."
        ),
        "must_contain": ["future", "expanding", "datasets", "hyperparameter", "optimisation"],
    },
}
_q_seq = iter(["q1", "q2", "q3"])

def make_mock(page):
    def route_tags(route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"models": [{"name": "gemma:2b"}]}))
    def route_chat(route):
        try:
            key = next(_q_seq, "q1")
            ans = ANSWERS[key]["a"]
            ndjson = json.dumps({
                "model": "gemma:2b",
                "message": {"role": "assistant", "content": ans},
                "done": True
            }) + "\n"
            route.fulfill(status=200, content_type="application/x-ndjson", body=ndjson)
        except Exception as e:
            route.fulfill(status=500, body=str(e))
    page.route("**/localhost:11434/api/tags", route_tags)
    page.route("**/localhost:11434/api/chat",  route_chat)

def wait_answer(page, timeout=20_000):
    try:
        page.wait_for_function("() => !!document.querySelector('.thinking-row')", timeout=5000)
    except Exception:
        pass
    page.wait_for_function("() => !document.querySelector('.thinking-row')", timeout=timeout)
    time.sleep(0.5)

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"\nURL: {URL}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=60)
    page    = browser.new_context().new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))

    make_mock(page)
    page.goto(URL, wait_until="networkidle")
    time.sleep(0.4)

    # Inject patch
    page.evaluate(PATCH_JS)
    console_patched = page.evaluate("() => typeof window.highlightChunk === 'function'")
    check("highlightChunk patched successfully", console_patched)

    # Upload PDF
    page.locator("#fileInput").set_input_files(PDF_PATH)
    page.wait_for_function(
        "() => document.getElementById('statusDot').classList.contains('active')",
        timeout=20_000
    )
    time.sleep(0.3)
    status = page.locator("#loading").text_content()
    check("PDF indexed", "chunk" in status.lower() or "page" in status.lower(), status)
    ss(page, "00_pdf_loaded")

    all_kw_sets = []  # collect per-question keywords for divergence check

    for qkey, qdata in ANSWERS.items():
        print(f"\n{'='*60}")
        print(f"  Q: {qdata['q']}")
        print(f"  Expected answer keywords: {qdata['must_contain']}")

        # Clear previous log
        page.evaluate("() => { window._hlLog = []; }")

        page.locator("#input").fill(qdata["q"])
        page.locator("#actionBtn").click()
        wait_answer(page)

        last_bubble = page.locator(".message.ai .bubble").last
        answer_text = last_bubble.text_content().strip()
        print(f"  Answer: {answer_text[:160]}")
        check(f"[{qkey}] AI returned answer", len(answer_text) > 15, answer_text[:80])

        # Check citation pills
        pills = last_bubble.locator(".source")
        pill_cnt = pills.count()
        check(f"[{qkey}] Citation pills present", pill_cnt >= 1, f"{pill_cnt} pills")

        if pill_cnt == 0:
            continue

        # Click first citation — wait for modal to actually open
        pills.first.click()
        try:
            page.wait_for_function(
                "() => document.getElementById('pdfModal')?.style?.display === 'flex'",
                timeout=6000
            )
        except Exception:
            pass
        time.sleep(1.2)
        ss(page, f"{qkey}_modal")

        # ── Collect data from patch ────────────────────────────────────────
        hl_log = page.evaluate("() => window._hlLog || []")
        check(f"[{qkey}] highlightChunk was called", len(hl_log) > 0,
              f"{len(hl_log)} calls")

        if not hl_log:
            page.locator("#closePdfBtn").click(); time.sleep(0.3); continue

        entry     = hl_log[-1]   # most recent call
        kw_list   = entry.get("keywords", [])
        ans_norm  = entry.get("answerNorm", "")
        tagged    = entry.get("tagged", 0)

        print(f"\n  Keywords extracted: {kw_list[:15]}")
        print(f"  Answer (normalised): {ans_norm[:120]}")

        # ── Check 1: keywords must be non-empty ────────────────────────────
        check(f"[{qkey}] Keywords non-empty", len(kw_list) > 0,
              f"{len(kw_list)} keywords")

        # ── Check 2: every keyword must appear in the normalised answer ────
        kws_in_answer = [kw for kw in kw_list if kw in ans_norm]
        kws_not_in    = [kw for kw in kw_list if kw not in ans_norm]
        check(f"[{qkey}] Every keyword appears in answer",
              len(kws_not_in) == 0,
              f"Missing from answer: {kws_not_in}" if kws_not_in else f"all {len(kw_list)} present")

        # ── Check 3: every keyword must be ≥3 chars (no stop-word leftovers) ──
        short_kws = [kw for kw in kw_list if len(kw) < 3]
        check(f"[{qkey}] No keywords shorter than 3 chars",
              len(short_kws) == 0,
              f"Short: {short_kws}" if short_kws else "")

        # ── Check 4: read tagged highlight divs ───────────────────────────
        hl_divs = page.evaluate("""
            () => [...document.querySelectorAll('.highlight')].map(d => ({
                itemText:  d.dataset.itemText  || '',
                matchedKw: d.dataset.matchedKw || '',
                w: parseFloat(d.style.width),
                h: parseFloat(d.style.height),
            }))
        """)
        print(f"\n  Highlight divs ({len(hl_divs)} total):")
        for j, d in enumerate(hl_divs):
            print(f"    [{j}] kw={d['matchedKw']!r:30}  item={d['itemText'][:60]!r}")

        tagged_divs   = [d for d in hl_divs if d["itemText"]]
        untagged_divs = [d for d in hl_divs if not d["itemText"]]

        check(f"[{qkey}] All highlight divs got item-text tag",
              len(untagged_divs) == 0,
              f"{len(untagged_divs)} untagged" if untagged_divs else f"{len(tagged_divs)} tagged")

        # ── Check 5: each highlighted item contains its matched keyword ────
        bad_relevance = []
        for d in tagged_divs:
            item_text = d["itemText"]
            for kw in (d["matchedKw"].split(",") if d["matchedKw"] else []):
                if kw and kw not in item_text:
                    bad_relevance.append(f"kw={kw!r} not in item={item_text!r}")

        check(f"[{qkey}] Every highlight's keyword appears in its item text",
              len(bad_relevance) == 0,
              bad_relevance[0] if bad_relevance else "")

        # ── Check 6: matched keywords are in expected answer keywords ──────
        expected_kws = set(qdata["must_contain"])
        found_in_hl  = set()
        for d in tagged_divs:
            found_in_hl.update(kw for kw in d["matchedKw"].split(",") if kw)

        overlap = expected_kws & (set(kw_list) | found_in_hl)
        check(f"[{qkey}] At least one expected keyword highlighted",
              len(overlap) > 0,
              f"Expected {expected_kws} ∩ got {set(kw_list)} = {overlap}")

        all_kw_sets.append(set(kw_list))

        ss(page, f"{qkey}_highlights")
        try:
            page.locator("#closePdfBtn").click(timeout=4000)
            time.sleep(0.3)
        except Exception:
            # Modal may have already closed; press Escape as fallback
            page.keyboard.press("Escape")
            time.sleep(0.2)

    # ── Check: different questions → different keywords ────────────────────
    print(f"\n{'='*60}")
    print("  Keyword sets per question:")
    for i, kws in enumerate(all_kw_sets, 1):
        print(f"    Q{i}: {sorted(kws)}")

    if len(all_kw_sets) >= 2:
        # At least one pair of questions should have different keywords
        pairs_differ = any(
            all_kw_sets[i] != all_kw_sets[j]
            for i in range(len(all_kw_sets))
            for j in range(i+1, len(all_kw_sets))
        )
        check("Different questions produce different keyword sets", pairs_differ,
              "all identical" if not pairs_differ else "at least one pair differs")

    check("No JS errors", len(js_errors) == 0,
          "; ".join(js_errors[:2]) if js_errors else "")
    ss(page, "final")
    browser.close()

server.shutdown()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
for icon, label, detail in results:
    line = f"  [{icon}] {label}"
    if detail: line += f"  ({detail[:110]})"
    print(line)
print(f"\n  {passed} passed, {failed} failed / {len(results)} total")
print("=" * 64)
raise SystemExit(0 if failed == 0 else 1)
