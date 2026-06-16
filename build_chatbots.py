"""Build Chatbot_V4.html and Chatbot_V3.html with V3 glassmorphism UI."""
import re

# ── Read V3 CSS ──────────────────────────────────────────────────────────────
with open(r'Chatbot_AI\pdf_chatbot_V3.html', 'r', encoding='utf-8') as f:
    v3_src = f.read()

style_start = v3_src.index('<style nonce="pdf-v3-style">') + len('<style nonce="pdf-v3-style">')
style_end   = v3_src.index('</style>')
V3_CSS = v3_src[style_start:style_end].strip()

# ── Shared extra CSS (connect button + data modal) ───────────────────────────
EXTRA_CSS = """
/* ── CONNECT BUTTON ── */
.connect-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  height: 36px; background: var(--accent-dim); border: 1px solid var(--accent-border);
  color: var(--accent); border-radius: var(--radius-sm); cursor: pointer;
  font-size: 12px; font-weight: 500; font-family: var(--font-body); transition: all 0.2s ease;
}
.connect-btn:hover { background: rgba(167,139,250,0.28); border-color: rgba(167,139,250,0.6); transform: translateY(-1px); }
.connect-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* ── DATA MODAL ── */
.data-modal {
  position: fixed; inset: 0; background: rgba(5,3,18,0.88); z-index: 9999;
  display: none; flex-direction: column; animation: fadeIn 0.25s var(--ease-out) forwards;
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
}
.data-toolbar {
  height: 62px; background: rgba(255,255,255,0.06); backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px); display: flex; align-items: center;
  justify-content: space-between; padding: 0 28px;
  border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--ink); gap: 16px;
}
#dataRecordInfo {
  font-family: var(--font-mono); font-size: 11.5px; font-weight: 500;
  letter-spacing: 0.08em; color: var(--ink-soft); text-transform: uppercase;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
#closeDataBtn {
  height: 34px; padding: 0 16px; border: 1px solid var(--line);
  background: transparent; color: var(--ink-soft); border-radius: 999px;
  cursor: pointer; font-size: 11.5px; font-weight: 500; font-family: var(--font-mono);
  letter-spacing: 0.04em; transition: all 0.2s ease; flex-shrink: 0;
}
#closeDataBtn:hover { background: #e53e3e; color: #fff; border-color: #e53e3e; box-shadow: 0 4px 14px rgba(229,62,62,0.3); }
.data-viewer { flex: 1; overflow: auto; padding: 32px; }
.data-viewer::-webkit-scrollbar { width: 8px; height: 8px; }
.data-viewer::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }
#dataContent {
  background: rgba(0,0,0,0.4); color: rgba(255,255,255,0.85);
  border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius);
  padding: 24px 28px; font-family: var(--font-mono); font-size: 12.5px;
  line-height: 1.7; white-space: pre-wrap; word-break: break-all;
  max-width: 960px; margin: 0 auto;
}
"""

# ── Shared HTML snippets ──────────────────────────────────────────────────────
TOPBAR_TOGGLE = '''      <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar" aria-label="Toggle sidebar">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>'''

INPUT_AREA = '''    <div class="input-area">
      <div class="input-row">
        <textarea id="input" placeholder="Connect an API, then ask anything…"></textarea>
        <button id="actionBtn" class="action-btn send" aria-label="Send message">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
        </button>
      </div>
    </div>'''

WELCOME_MSG = '''    <div class="chat" id="chat">
      <div class="message ai" id="welcomeMsg">
        <div class="bubble">
          <div class="empty-hint">
            <span class="em-greeting" id="emGreeting"></span>
            <span class="em-title" id="emTitle"></span>
            <span class="em-sub" id="emSub"></span>
          </div>
        </div>
      </div>
    </div>'''

DATA_MODAL = '''<div id="dataModal" class="data-modal" role="dialog" aria-modal="true" aria-labelledby="dataRecordInfo">
  <div class="data-toolbar">
    <div id="dataRecordInfo">Record Viewer</div>
    <button id="closeDataBtn" type="button">Close ✕</button>
  </div>
  <div class="data-viewer"><pre id="dataContent"></pre></div>
</div>'''

SOURCE_CARD_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'''

CONNECT_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>'''

# ── Shared JS helpers ─────────────────────────────────────────────────────────
STOP_SEND_JS = """
// ── STOP / SEND STATE ────────────────────────────────────────────────────────
let currentController = null;
const TIMEOUT_MS = 120_000;
const _ICON_SEND = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>';
const _ICON_STOP = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="3"/></svg>';
function showStop() { const b=document.getElementById("actionBtn"); b.innerHTML=_ICON_STOP; b.className="action-btn stop"; b.setAttribute("aria-label","Stop"); b.disabled=false; }
function showSend() { const b=document.getElementById("actionBtn"); b.innerHTML=_ICON_SEND; b.className="action-btn send"; b.setAttribute("aria-label","Send message"); b.disabled=false; }
function stopGeneration() { if(currentController) currentController.abort("user"); }
"""

MOBILE_SIDEBAR_JS = """
// ── SIDEBAR TOGGLE ────────────────────────────────────────────────────────────
function isMobile() { return window.matchMedia("(max-width: 640px)").matches; }
function openMobileSidebar() { document.getElementById("sidebar").classList.add("mobile-open"); document.getElementById("sidebarBackdrop").classList.add("visible"); document.body.style.overflow="hidden"; }
function closeMobileSidebar() { document.getElementById("sidebar").classList.remove("mobile-open"); document.getElementById("sidebarBackdrop").classList.remove("visible"); document.body.style.overflow=""; }
document.getElementById("sidebarToggle").addEventListener("click", () => {
  if (isMobile()) { document.getElementById("sidebar").classList.contains("mobile-open") ? closeMobileSidebar() : openMobileSidebar(); }
  else { document.querySelector(".container").classList.toggle("sidebar-collapsed"); }
});
document.getElementById("sidebarBackdrop").addEventListener("click", closeMobileSidebar);
"""

GREETING_JS = """
// ── GREETING ─────────────────────────────────────────────────────────────────
(function() {
  const h = new Date().getHours();
  let emoji, period, prompt;
  if (h>=5&&h<12)       { emoji="☀️";  period="Good Morning";   prompt="What would you like to explore today?"; }
  else if (h>=12&&h<17) { emoji="🌤️"; period="Good Afternoon"; prompt="What can I help you find in your data?"; }
  else if (h>=17&&h<21) { emoji="🌙";  period="Good Evening";   prompt="Ready to dive into your data?"; }
  else                  { emoji="🌃";  period="Working late?";  prompt="I'm here whenever you need me."; }
  const g=document.getElementById("emGreeting"), t=document.getElementById("emTitle"), s=document.getElementById("emSub");
  if(g) g.textContent=`${emoji}  ${period}`;
  if(t) t.textContent=prompt;
  if(s) s.textContent="Connect an API using the sidebar, then ask me anything about the data.";
})();
"""

COMMON_LISTENERS = """
document.getElementById("apiMethod").addEventListener("change", function() {
  document.getElementById("apiBody").style.display = this.value === "POST" ? "block" : "none";
});
document.getElementById("connectBtn").addEventListener("click", connectAPI);
document.getElementById("apiUrl").addEventListener("keydown", e => { if (e.key === "Enter") connectAPI(); });
document.getElementById("actionBtn").addEventListener("click", () => {
  if (document.getElementById("actionBtn").classList.contains("stop")) stopGeneration();
  else sendMessage();
});
document.getElementById("closeDataBtn").addEventListener("click", closeDataViewer);
document.getElementById("dataModal").addEventListener("click", e => { if (e.target === e.currentTarget) closeDataViewer(); });
document.getElementById("input").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
document.getElementById("input").addEventListener("input", function() { this.style.height = "52px"; this.style.height = Math.min(this.scrollHeight, 140) + "px"; });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDataViewer(); });
"""

# ══════════════════════════════════════════════════════════════════════════════
# CHATBOT V4 — Ollama + REST API
# ══════════════════════════════════════════════════════════════════════════════

V4_SIDEBAR = f'''  <aside class="sidebar" id="sidebar">
    <div class="sidebar-top">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">Ai</div>
        <div class="brand-copy">
          <h1>API AI Assistant</h1>
          <p>Ollama · local model</p>
        </div>
      </div>
    </div>

    <div class="model-section">
      <div class="panel-label">Ollama Model</div>
      <div class="model-row">
        <input type="text" class="model-input" id="ollamaModel" value="gemma:2b" placeholder="gemma:2b" autocomplete="off" spellcheck="false" aria-label="Ollama model name">
        <button class="ping-btn" id="pingBtn" type="button" title="Check Ollama">●</button>
      </div>
    </div>

    <div class="model-section">
      <div class="panel-label">Context Size</div>
      <select class="model-input" id="contextSize" style="cursor:pointer;">
        <option value="tiny">Tiny — 1 chunk · 300 chars</option>
        <option value="small" selected>Small — 2 chunks · 800 chars</option>
        <option value="medium">Medium — 3 chunks · 2500 chars</option>
        <option value="large">Large — 5 chunks · 5000 chars</option>
      </select>
    </div>

    <div class="model-section" style="flex:1;overflow-y:auto;gap:8px;">
      <div class="panel-label">Data Source</div>
      <div class="doc-card">
        <div class="doc-card-icon" id="sourceIcon">{SOURCE_CARD_SVG}</div>
        <div class="doc-card-body">
          <div class="doc-name" id="sourceName">No source connected</div>
          <div class="doc-meta" id="sourceMeta">Enter an API URL below</div>
        </div>
      </div>
      <input type="url" class="model-input" id="apiUrl" placeholder="https://api.example.com/data" autocomplete="off" spellcheck="false">
      <input type="text" class="model-input" id="apiAuth" placeholder="Authorization: Bearer &lt;token&gt;" autocomplete="off" spellcheck="false">
      <div style="display:flex;gap:8px;">
        <select class="model-input" id="apiMethod" style="flex:0 0 auto;width:70px;cursor:pointer;">
          <option value="GET">GET</option><option value="POST">POST</option>
        </select>
        <button class="connect-btn" id="connectBtn" type="button">{CONNECT_SVG} Connect</button>
      </div>
      <textarea class="model-input" id="apiBody" placeholder=\'{{"key":"value"}}\' style="display:none;resize:vertical;min-height:72px;max-height:140px;"></textarea>
    </div>

    <div class="status-card">
      <div class="panel-label">Status</div>
      <div class="status-indicator">
        <div class="status-dot" id="statusDot"></div>
        <div class="loading" id="loading" role="status" aria-live="polite">Checking Ollama…</div>
      </div>
    </div>
  </aside>'''

V4_JS_CORE = """
const OLLAMA_BASE = "http://localhost:11434";
const CHUNK_SIZE = 150;
const CHUNK_OVERLAP = 15;
const CONTEXT_PROFILES = {
  tiny:   { topK: 1, charsPerChunk: 300,  maxTotal: 400  },
  small:  { topK: 2, charsPerChunk: 400,  maxTotal: 900  },
  medium: { topK: 3, charsPerChunk: 700,  maxTotal: 2500 },
  large:  { topK: 5, charsPerChunk: 900,  maxTotal: 5000 },
};
function getContextProfile() { const k=document.getElementById("contextSize")?.value||"small"; return CONTEXT_PROFILES[k]||CONTEXT_PROFILES.small; }

const SAFE_MARKDOWN_TAGS=["p","h1","h2","h3","h4","strong","em","code","pre","hr","ul","ol","li","div","table","thead","tbody","tr","th","td"];
const SAFE_MARKDOWN_ATTRS=["class","aria-hidden"];
let chunks=[],embeddings=[];

function setStatus(t,s){const d=document.getElementById("statusDot"),e=document.getElementById("loading");if(e)e.textContent=t;if(d)d.className="status-dot"+(s?" "+s:"");}

function updateSourceName(name) {
  const nm=document.getElementById("sourceName"),mt=document.getElementById("sourceMeta"),ic=document.getElementById("sourceIcon");
  if(nm){nm.textContent=name||"No source connected";nm.classList.toggle("has-file",Boolean(name));}
  if(mt&&!name)mt.textContent="Enter an API URL below";
  if(ic)ic.classList.toggle("has-file",Boolean(name));
}

function escapeHtml(t){const d=document.createElement("div");d.textContent=t;return d.innerHTML;}
function decodeHtmlEntities(t){const a=document.createElement("textarea");a.innerHTML=String(t||"");return a.value;}
function stripRawHtmlPayloads(t){return String(t||"").replace(/<\\s*\\/? \\s*[a-z][a-z0-9:-]*(?:\\s+[^<>]*)?\\s*\\/? \\s*>/gi," ").replace(/\\b(?:javascript|vbscript)\\s*:/gi," ").replace(/\\bon[a-z]+\\s*=/gi," ").replace(/<\\/?(?:script|style|iframe|object|embed|svg|math|meta|link|base|form|input|button|textarea|select|option|img|video|audio|source|canvas|frame|frameset|applet|template)[^>]*>/gi," ").replace(/[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]/g,"");}
function renderInlineMarkdown(t){return escapeHtml(t).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\\*\\*([^*]+)\\*\\*/g,"<strong>$1</strong>").replace(/__([^_]+)__/g,"<strong>$1</strong>").replace(/\\*([^*]+)\\*/g,"<em>$1</em>").replace(/_([^_]+)_/g,"<em>$1</em>");}
function normalizeMessageText(t){return stripRawHtmlPayloads(decodeHtmlEntities(t)).replace(/\\r\\n/g,"\\n").replace(/<br\\s*\\/?>/gi,"\\n").replace(/(\\S)\\s*\\|\\s*\\|\\s*(?=\\S)/g,"$1\\n| ");}
function sanitizeRenderedHtml(html){const dp=window.DOMPurify;if(dp)return dp.sanitize(html,{ALLOWED_TAGS:SAFE_MARKDOWN_TAGS,ALLOWED_ATTR:SAFE_MARKDOWN_ATTRS,ALLOW_DATA_ATTR:false,FORBID_TAGS:["script","style","iframe","form","img","svg"],FORBID_ATTR:["style","src","href","onerror","onload"]});const tpl=document.createElement("template");tpl.innerHTML=html;const ok=new Set(["P","H1","H2","H3","H4","STRONG","EM","CODE","PRE","HR","UL","OL","LI","DIV","TABLE","THEAD","TBODY","TR","TH","TD"]);tpl.content.querySelectorAll("*").forEach(el=>{if(!ok.has(el.tagName)){el.replaceWith(document.createTextNode(el.textContent||""));return;}[...el.attributes].forEach(a=>{if(a.name!=="class")el.removeAttribute(a.name);});});return tpl.innerHTML;}

function isTableSeparator(l){return /^\\s*\\|?\\s*:?-{3,}:?\\s*(\\|\\s*:?-{3,}:?\\s*)+\\|?\\s*$/.test(l);}
function isTableRow(l){return l.trim().includes("|");}
function splitTableRow(l){return l.trim().replace(/^\\|/,"").replace(/\\|$/,"").split("|").map(c=>c.trim());}
function renderMarkdownTable(lines){const hs=splitTableRow(lines[0]),rs=lines.slice(2).filter(isTableRow).map(splitTableRow);return `<div class="table-wrap"><table><thead><tr>${hs.map(h=>`<th>${renderInlineMarkdown(h)}</th>`).join("")}</tr></thead><tbody>${rs.map(r=>`<tr>${hs.map((_,i)=>`<td>${renderInlineMarkdown(r[i]||"")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
function flushP(pl,hp){if(!pl.length)return;hp.push(`<p>${renderInlineMarkdown(pl.join(" "))}</p>`);pl.length=0;}
function flushL(li,lt,hp){if(!li.length)return;const t=lt==="ol"?"ol":"ul";hp.push(`<${t}>${li.map(i=>`<li>${renderInlineMarkdown(i)}</li>`).join("")}</${t}>`);li.length=0;}
function markdownToHtml(text){const lines=normalizeMessageText(text).split("\\n"),hp=[],pl=[],li=[];let lt=null,inC=false,cl=[];for(let i=0;i<lines.length;i++){const l=lines[i];if(l.trim().startsWith("```")){if(inC){hp.push(`<pre><code>${escapeHtml(cl.join("\\n"))}</code></pre>`);cl=[];inC=false;}else{flushP(pl,hp);flushL(li,lt,hp);lt=null;inC=true;}continue;}if(inC){cl.push(l);continue;}if(/^\\s*(?:-{3,}|\\*{3,}|_{3,})\\s*$/.test(l)){flushP(pl,hp);flushL(li,lt,hp);lt=null;hp.push("<hr>");continue;}if(i+1<lines.length&&isTableRow(l)&&isTableSeparator(lines[i+1])){flushP(pl,hp);flushL(li,lt,hp);lt=null;const tbl=[l,lines[i+1]];i+=2;while(i<lines.length&&isTableRow(lines[i])&&lines[i].trim()){tbl.push(lines[i]);i++;}i--;hp.push(renderMarkdownTable(tbl));continue;}const hm=l.match(/^\\s*(#{1,4})\\s+(.+)$/);if(hm){flushP(pl,hp);flushL(li,lt,hp);lt=null;hp.push(`<h${hm[1].length}>${renderInlineMarkdown(hm[2])}</h${hm[1].length}>`);continue;}const nm=l.match(/^\\s*\\d+\\.\\s+(.+)$/),bm=l.match(/^\\s*[-*]\\s+(.+)$/);if(nm){flushP(pl,hp);if(lt&&lt!=="ol")flushL(li,lt,hp);lt="ol";li.push(nm[1]);continue;}if(bm){flushP(pl,hp);if(lt&&lt!=="ul")flushL(li,lt,hp);lt="ul";li.push(bm[1]);continue;}if(!l.trim()){flushP(pl,hp);flushL(li,lt,hp);lt=null;continue;}flushL(li,lt,hp);lt=null;pl.push(l.trim());}if(inC)hp.push(`<pre><code>${escapeHtml(cl.join("\\n"))}</code></pre>`);flushP(pl,hp);flushL(li,lt,hp);return sanitizeRenderedHtml(hp.join(""));}
function markdownToFragment(text){const t=document.createElement("template");t.innerHTML=markdownToHtml(text);return t.content.cloneNode(true);}

// ── OLLAMA PING ───────────────────────────────────────────────────────────────
async function pingOllama() {
  const btn = document.getElementById("pingBtn");
  btn.className = "ping-btn"; btn.textContent = "●";
  try {
    const res = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    btn.className = "ping-btn ok";
    const names = (data.models||[]).map(m=>m.name).join(", ");
    setStatus(`Ollama ready · ${data.models?.length||0} model(s)${names?": "+names:""}`, "active");
    return true;
  } catch(err) {
    btn.className = "ping-btn fail";
    const isCors = err instanceof TypeError || err.message === "Failed to fetch";
    setStatus(isCors ? "CORS blocked — run: OLLAMA_ORIGINS=* ollama serve" : `Ollama not reachable — is 'ollama serve' running?`, "");
    return false;
  }
}

// ── TF RETRIEVAL ──────────────────────────────────────────────────────────────
function tokenize(t){return t.toLowerCase().replace(/[^a-z0-9\\s]/g," ").split(/\\s+/).filter(Boolean);}
async function buildEmbeddings(docs){const r=[];for(let i=0;i<docs.length;i++){const tf={};tokenize(docs[i].text).forEach(t=>{tf[t]=(tf[t]||0)+1;});r.push(tf);if(i%50===0)await new Promise(x=>setTimeout(x,0));}return r;}
function cosine(a,b){let dot=0,mA=0,mB=0;const ks=new Set([...Object.keys(a),...Object.keys(b)]);ks.forEach(k=>{dot+=(a[k]||0)*(b[k]||0);mA+=(a[k]||0)**2;mB+=(b[k]||0)**2;});return(mA===0||mB===0)?0:dot/(Math.sqrt(mA)*Math.sqrt(mB));}
function retrieve(query,topK){const q={};tokenize(query).forEach(t=>{q[t]=(q[t]||0)+1;});return embeddings.map((e,i)=>({index:i,score:cosine(q,e)})).sort((a,b)=>b.score-a.score).slice(0,topK);}

// ── DATA PROCESSING ───────────────────────────────────────────────────────────
function stripHtml(s){return s.replace(/<[^>]*>/g," ").replace(/&nbsp;/g," ").replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/\\s+/g," ").trim();}
function jsonToText(v){if(v===null||v===undefined)return "";if(typeof v==="string")return v.includes("<")?stripHtml(v):v;if(typeof v==="number"||typeof v==="boolean")return String(v);if(Array.isArray(v))return v.map(x=>jsonToText(x)).join(" ");if(typeof v==="object")return Object.entries(v).map(([k,x])=>`${k}: ${jsonToText(x)}`).join(" ");return String(v);}
function getRecordLabel(item,index){if(typeof item==="object"&&item!==null){for(const f of["name","title","label","id","key","slug","username","email","subject","description"]){if(item[f]!==undefined&&item[f]!==null&&String(item[f]).trim())return String(item[f]).slice(0,48);}}return `Record ${index+1}`;}
function unwrapEnvelope(r){if(!r||typeof r!=="object"||Array.isArray(r))return r;for(const k of["data","result","results","items","records","rows","content","payload","body","list","response"]){if(r[k]!==undefined&&r[k]!==null){const v=r[k];if(Array.isArray(v)||(typeof v==="object"&&Object.keys(v).length>0))return v;}}return r;}
function buildChunks(data){const result=[];if(Array.isArray(data)){data.forEach((item,i)=>result.push({text:jsonToText(item),label:getRecordLabel(item,i),raw:item,index:i}));return result;}if(typeof data==="object"&&data!==null){const entries=Object.entries(data);if(entries.length<=30){entries.forEach(([key,value],i)=>result.push({text:`${key}: ${jsonToText(value)}`,label:key,raw:{[key]:value},index:i}));return result;}}const fullText=typeof data==="string"?data:JSON.stringify(data,null,2),words=fullText.split(/\\s+/);let start=0;while(start<words.length){const end=Math.min(start+CHUNK_SIZE,words.length);result.push({text:words.slice(start,end).join(" "),label:`Chunk ${result.length+1}`,raw:words.slice(start,end).join(" "),index:result.length});if(end>=words.length)break;start+=CHUNK_SIZE-CHUNK_OVERLAP;}return result;}

// ── API CONNECTION ─────────────────────────────────────────────────────────────
async function connectAPI() {
  const urlInput=document.getElementById("apiUrl").value.trim(),auth=document.getElementById("apiAuth").value.trim(),method=document.getElementById("apiMethod").value,body=document.getElementById("apiBody").value.trim(),btn=document.getElementById("connectBtn");
  if(!urlInput){setStatus("Enter an API URL first.","");return;}
  setStatus("Connecting…","loading"); btn.disabled=true;
  try {
    const headers={};
    if(auth){const ci=auth.indexOf(":");if(ci>0&&ci<40){headers[auth.slice(0,ci).trim()]=auth.slice(ci+1).trim();}else{headers["Authorization"]=`Bearer ${auth}`;}}
    const options={method,headers};
    if(method==="POST"&&body){headers["Content-Type"]="application/json";options.body=body;}
    const response=await fetch(urlInput,options);
    if(!response.ok)throw new Error(`HTTP ${response.status} ${response.statusText}`);
    const ct=response.headers.get("content-type")||"";
    let data;
    if(ct.includes("application/json")){data=await response.json();}else{const text=await response.text();try{data=JSON.parse(text);}catch{data=text;}}
    const unwrapped=unwrapEnvelope(data);
    chunks=buildChunks(unwrapped);
    embeddings=await buildEmbeddings(chunks);
    let domain;try{domain=new URL(urlInput).hostname;}catch{domain=urlInput;}
    updateSourceName(domain);
    const mt=document.getElementById("sourceMeta");if(mt)mt.textContent=`${chunks.length} records indexed`;
    setStatus(`${chunks.length} records indexed`,"active");
    addMessage("ai",`Connected to **${domain}** — **${chunks.length}** records indexed.\\n\\nAsk me anything about the data.`);
  } catch(err) {
    setStatus(err.message,""); updateSourceName("");
    addMessage("ai",`Connection failed: **${err.message}**\\n\\n- Check the URL and CORS headers.`);
  } finally { btn.disabled=false; }
}

// ── CHAT ───────────────────────────────────────────────────────────────────────
function addMessage(role,text){const chat=document.getElementById("chat"),msg=document.createElement("div");msg.className=`message ${role}`;const bubble=document.createElement("div");bubble.className="bubble";if(text==="__thinking__"){const row=document.createElement("div");row.className="thinking-row";row.innerHTML='<div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div>';bubble.appendChild(row);}else{bubble.replaceChildren(markdownToFragment(text));}msg.appendChild(bubble);chat.appendChild(msg);chat.scrollTop=chat.scrollHeight;return msg;}

async function sendMessage() {
  const input=document.getElementById("input"),query=input.value.trim();
  if(!query)return;
  if(!chunks.length){addMessage("ai","Connect an API endpoint first, then ask questions.");return;}
  input.value=""; input.style.height="52px";
  addMessage("user",query);
  showStop();
  currentController=new AbortController();
  const {signal}=currentController;
  const timeoutId=setTimeout(()=>{if(currentController)currentController.abort("timeout");},TIMEOUT_MS);
  const profile=getContextProfile();
  const retrieved=retrieve(query,profile.topK);
  const context=retrieved.map(r=>{const text=chunks[r.index].text.slice(0,profile.charsPerChunk);return `[${chunks[r.index].label}]\\n${text}`;}).join("\\n---\\n").slice(0,profile.maxTotal);
  const modelName=document.getElementById("ollamaModel").value.trim()||"gemma:2b";
  const thinkingMsg=addMessage("ai","__thinking__");
  let streamBubble=null,fullText="";
  try {
    const response=await fetch(`${OLLAMA_BASE}/api/chat`,{method:"POST",headers:{"Content-Type":"application/json"},signal,body:JSON.stringify({model:modelName,messages:[{role:"system",content:"Answer questions using ONLY the data provided. Be concise. If the answer is not in the data, say so."},{role:"user",content:`API Data Context:\\n\\n${context}\\n\\nQuestion:\\n${query}`}],options:{temperature:0.2},stream:true})});
    thinkingMsg.remove();
    if(!response.ok){const b=await response.text().catch(()=>"");addMessage("ai",`Ollama error HTTP ${response.status}${b?": "+b:""}`);return;}
    const aiMsg=addMessage("ai","");streamBubble=aiMsg.querySelector(".bubble");
    const chat=document.getElementById("chat"),reader=response.body.getReader(),dec=new TextDecoder();let buf="";
    while(true){const{done,value}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});const lines=buf.split("\\n");buf=lines.pop();for(const line of lines){if(!line.trim())continue;try{const obj=JSON.parse(line),token=obj.message?.content;if(token){fullText+=token;streamBubble.replaceChildren(markdownToFragment(fullText));chat.scrollTop=chat.scrollHeight;}}catch{}}}
    if(!fullText){streamBubble.replaceChildren(markdownToFragment("No response."));return;}
  } catch(err) {
    if(thinkingMsg.isConnected)thinkingMsg.remove();
    if(err.name==="AbortError"||signal.aborted){
      const reason=signal.reason;
      if(streamBubble){if(!fullText){streamBubble.replaceChildren(markdownToFragment("*Generation stopped.*"));}else{const badge=document.createElement("span");badge.className="stopped-badge";badge.textContent=reason==="timeout"?" [timed out]":" [stopped]";streamBubble.appendChild(badge);}}
      else{addMessage("ai",reason==="timeout"?"*Ollama took too long to respond.*":"*Generation stopped.*");}
    } else {
      const isCors=err instanceof TypeError||err.message==="Failed to fetch";
      if(isCors)addMessage("ai","**CORS error** — run: `OLLAMA_ORIGINS=* ollama serve`");
      else addMessage("ai",`Failed to reach Ollama: **${err.message}**`);
    }
  } finally { clearTimeout(timeoutId); currentController=null; showSend(); }
}

// ── RECORD VIEWER ──────────────────────────────────────────────────────────────
function openRecord(chunkIndex){const chunk=chunks[chunkIndex];if(!chunk)return;document.getElementById("dataRecordInfo").textContent=chunk.label;document.getElementById("dataContent").textContent=typeof chunk.raw==="object"?JSON.stringify(chunk.raw,null,2):String(chunk.raw);document.getElementById("dataModal").style.display="flex";}
function closeDataViewer(){document.getElementById("dataModal").style.display="none";}
"""

def build_html(nonce_style, nonce_script, title, csp_connect, sidebar_html, topbar_extra, extra_js, pill_text, subtitle):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'self'; base-uri 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; frame-ancestors 'none'; script-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com 'nonce-{nonce_script}'; connect-src 'self' {csp_connect}; img-src 'self' data: blob:; style-src 'self' 'nonce-{nonce_style}' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; upgrade-insecure-requests"
>
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@300;400;500&family=Geist:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.2.6/purify.min.js"></script>
<style nonce="{nonce_style}">
{V3_CSS}
{EXTRA_CSS}
</style>
</head>
<body>
<div class="sidebar-backdrop" id="sidebarBackdrop"></div>
<div class="container">

{sidebar_html}

  <main class="workspace">
    <div class="topbar">
{TOPBAR_TOGGLE}
      <div class="topbar-title">
        <h2>Ask your API</h2>
        <p>{subtitle}</p>
      </div>
      <div class="topbar-pill">{pill_text}</div>
    </div>

{WELCOME_MSG}

{INPUT_AREA}
  </main>
</div>

{DATA_MODAL}

<script nonce="{nonce_script}">
{extra_js}
{STOP_SEND_JS}
{COMMON_LISTENERS}
{MOBILE_SIDEBAR_JS}
{GREETING_JS}
</script>
</body>
</html>"""

# ── Write Chatbot_V4.html ────────────────────────────────────────────────────
v4_html = build_html(
    nonce_style="cv4-style",
    nonce_script="cv4-script",
    title="API Chatbot — Ollama",
    csp_connect="http://localhost:11434 http://127.0.0.1:11434 http: https:",
    sidebar_html=V4_SIDEBAR,
    topbar_extra="",
    extra_js=V4_JS_CORE + "\n// Auto-check on load\npingOllama();\ndocument.getElementById('pingBtn').addEventListener('click', pingOllama);\ndocument.getElementById('ollamaModel').addEventListener('keydown', e => { if(e.key==='Enter') pingOllama(); });",
    pill_text="Ollama · Local",
    subtitle="Connect any REST endpoint, ask questions, click records to inspect raw data."
)

with open(r'Chatbot_AI\Chatbot_V4.html', 'w', encoding='utf-8') as f:
    f.write(v4_html)
print("Chatbot_V4.html written:", len(v4_html), "chars")

# ══════════════════════════════════════════════════════════════════════════════
# CHATBOT V3 — Groq + REST API
# ══════════════════════════════════════════════════════════════════════════════

V3_SIDEBAR = f'''  <aside class="sidebar" id="sidebar">
    <div class="sidebar-top">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">Ai</div>
        <div class="brand-copy">
          <h1>API AI Assistant</h1>
          <p>Groq · cloud model</p>
        </div>
      </div>
    </div>

    <div class="model-section" style="flex:1;overflow-y:auto;gap:8px;">
      <div class="panel-label">Data Source</div>
      <div class="doc-card">
        <div class="doc-card-icon" id="sourceIcon">{SOURCE_CARD_SVG}</div>
        <div class="doc-card-body">
          <div class="doc-name" id="sourceName">No source connected</div>
          <div class="doc-meta" id="sourceMeta">Enter an API URL below</div>
        </div>
      </div>
      <input type="url" class="model-input" id="apiUrl" placeholder="https://api.example.com/data" autocomplete="off" spellcheck="false">
      <input type="text" class="model-input" id="apiAuth" placeholder="Authorization: Bearer &lt;token&gt;" autocomplete="off" spellcheck="false">
      <div style="display:flex;gap:8px;">
        <select class="model-input" id="apiMethod" style="flex:0 0 auto;width:70px;cursor:pointer;">
          <option value="GET">GET</option><option value="POST">POST</option>
        </select>
        <button class="connect-btn" id="connectBtn" type="button">{CONNECT_SVG} Connect</button>
      </div>
      <textarea class="model-input" id="apiBody" placeholder=\'{{"key":"value"}}\' style="display:none;resize:vertical;min-height:72px;max-height:140px;"></textarea>
    </div>

    <div class="status-card">
      <div class="panel-label">Status</div>
      <div class="status-indicator">
        <div class="status-dot" id="statusDot"></div>
        <div class="loading" id="loading" role="status" aria-live="polite">Idle — no source connected</div>
      </div>
    </div>
  </aside>'''

V3_JS_CORE = """
const GROQ_KEY_STORAGE = "groq_api_key_v3";
const TOP_K = 3;
const CHUNK_SIZE = 200;
const CHUNK_OVERLAP = 20;
const SAFE_MARKDOWN_TAGS=["p","h1","h2","h3","h4","strong","em","code","pre","hr","ul","ol","li","div","table","thead","tbody","tr","th","td"];
const SAFE_MARKDOWN_ATTRS=["class","aria-hidden"];
let chunks=[],embeddings=[];

function setStatus(t,s){const d=document.getElementById("statusDot"),e=document.getElementById("loading");if(e)e.textContent=t;if(d)d.className="status-dot"+(s?" "+s:"");}

function updateSourceName(name) {
  const nm=document.getElementById("sourceName"),mt=document.getElementById("sourceMeta"),ic=document.getElementById("sourceIcon");
  if(nm){nm.textContent=name||"No source connected";nm.classList.toggle("has-file",Boolean(name));}
  if(mt&&!name)mt.textContent="Enter an API URL below";
  if(ic)ic.classList.toggle("has-file",Boolean(name));
}

function escapeHtml(t){const d=document.createElement("div");d.textContent=t;return d.innerHTML;}
function decodeHtmlEntities(t){const a=document.createElement("textarea");a.innerHTML=String(t||"");return a.value;}
function stripRawHtmlPayloads(t){return String(t||"").replace(/<\\s*\\/? \\s*[a-z][a-z0-9:-]*(?:\\s+[^<>]*)?\\s*\\/? \\s*>/gi," ").replace(/\\b(?:javascript|vbscript)\\s*:/gi," ").replace(/\\bon[a-z]+\\s*=/gi," ").replace(/<\\/?(?:script|style|iframe|object|embed|svg|math|meta|link|base|form|input|button|textarea|select|option|img|video|audio|source|canvas|frame|frameset|applet|template)[^>]*>/gi," ").replace(/[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]/g,"");}
function renderInlineMarkdown(t){return escapeHtml(t).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\\*\\*([^*]+)\\*\\*/g,"<strong>$1</strong>").replace(/__([^_]+)__/g,"<strong>$1</strong>").replace(/\\*([^*]+)\\*/g,"<em>$1</em>").replace(/_([^_]+)_/g,"<em>$1</em>");}
function normalizeMessageText(t){return stripRawHtmlPayloads(decodeHtmlEntities(t)).replace(/\\r\\n/g,"\\n").replace(/<br\\s*\\/?>/gi,"\\n").replace(/(\\S)\\s*\\|\\s*\\|\\s*(?=\\S)/g,"$1\\n| ");}
function sanitizeRenderedHtml(html){const dp=window.DOMPurify;if(dp)return dp.sanitize(html,{ALLOWED_TAGS:SAFE_MARKDOWN_TAGS,ALLOWED_ATTR:SAFE_MARKDOWN_ATTRS,ALLOW_DATA_ATTR:false,FORBID_TAGS:["script","style","iframe","form","img","svg"],FORBID_ATTR:["style","src","href","onerror","onload"]});const tpl=document.createElement("template");tpl.innerHTML=html;const ok=new Set(["P","H1","H2","H3","H4","STRONG","EM","CODE","PRE","HR","UL","OL","LI","DIV","TABLE","THEAD","TBODY","TR","TH","TD"]);tpl.content.querySelectorAll("*").forEach(el=>{if(!ok.has(el.tagName)){el.replaceWith(document.createTextNode(el.textContent||""));return;}[...el.attributes].forEach(a=>{if(a.name!=="class")el.removeAttribute(a.name);});});return tpl.innerHTML;}

function isTableSeparator(l){return /^\\s*\\|?\\s*:?-{3,}:?\\s*(\\|\\s*:?-{3,}:?\\s*)+\\|?\\s*$/.test(l);}
function isTableRow(l){return l.trim().includes("|");}
function splitTableRow(l){return l.trim().replace(/^\\|/,"").replace(/\\|$/,"").split("|").map(c=>c.trim());}
function renderMarkdownTable(lines){const hs=splitTableRow(lines[0]),rs=lines.slice(2).filter(isTableRow).map(splitTableRow);return `<div class="table-wrap"><table><thead><tr>${hs.map(h=>`<th>${renderInlineMarkdown(h)}</th>`).join("")}</tr></thead><tbody>${rs.map(r=>`<tr>${hs.map((_,i)=>`<td>${renderInlineMarkdown(r[i]||"")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
function flushP(pl,hp){if(!pl.length)return;hp.push(`<p>${renderInlineMarkdown(pl.join(" "))}</p>`);pl.length=0;}
function flushL(li,lt,hp){if(!li.length)return;const t=lt==="ol"?"ol":"ul";hp.push(`<${t}>${li.map(i=>`<li>${renderInlineMarkdown(i)}</li>`).join("")}</${t}>`);li.length=0;}
function markdownToHtml(text){const lines=normalizeMessageText(text).split("\\n"),hp=[],pl=[],li=[];let lt=null,inC=false,cl=[];for(let i=0;i<lines.length;i++){const l=lines[i];if(l.trim().startsWith("```")){if(inC){hp.push(`<pre><code>${escapeHtml(cl.join("\\n"))}</code></pre>`);cl=[];inC=false;}else{flushP(pl,hp);flushL(li,lt,hp);lt=null;inC=true;}continue;}if(inC){cl.push(l);continue;}if(/^\\s*(?:-{3,}|\\*{3,}|_{3,})\\s*$/.test(l)){flushP(pl,hp);flushL(li,lt,hp);lt=null;hp.push("<hr>");continue;}if(i+1<lines.length&&isTableRow(l)&&isTableSeparator(lines[i+1])){flushP(pl,hp);flushL(li,lt,hp);lt=null;const tbl=[l,lines[i+1]];i+=2;while(i<lines.length&&isTableRow(lines[i])&&lines[i].trim()){tbl.push(lines[i]);i++;}i--;hp.push(renderMarkdownTable(tbl));continue;}const hm=l.match(/^\\s*(#{1,4})\\s+(.+)$/);if(hm){flushP(pl,hp);flushL(li,lt,hp);lt=null;hp.push(`<h${hm[1].length}>${renderInlineMarkdown(hm[2])}</h${hm[1].length}>`);continue;}const nm=l.match(/^\\s*\\d+\\.\\s+(.+)$/),bm=l.match(/^\\s*[-*]\\s+(.+)$/);if(nm){flushP(pl,hp);if(lt&&lt!=="ol")flushL(li,lt,hp);lt="ol";li.push(nm[1]);continue;}if(bm){flushP(pl,hp);if(lt&&lt!=="ul")flushL(li,lt,hp);lt="ul";li.push(bm[1]);continue;}if(!l.trim()){flushP(pl,hp);flushL(li,lt,hp);lt=null;continue;}flushL(li,lt,hp);lt=null;pl.push(l.trim());}if(inC)hp.push(`<pre><code>${escapeHtml(cl.join("\\n"))}</code></pre>`);flushP(pl,hp);flushL(li,lt,hp);return sanitizeRenderedHtml(hp.join(""));}
function markdownToFragment(text){const t=document.createElement("template");t.innerHTML=markdownToHtml(text);return t.content.cloneNode(true);}

// ── API KEY ────────────────────────────────────────────────────────────────────
function getApiKey(){let k=localStorage.getItem(GROQ_KEY_STORAGE);if(k)return k;k=window.prompt("Enter your Groq API key");if(!k)return "";k=k.trim();localStorage.setItem(GROQ_KEY_STORAGE,k);return k;}

// ── TF RETRIEVAL ──────────────────────────────────────────────────────────────
function tokenize(t){return t.toLowerCase().replace(/[^a-z0-9\\s]/g," ").split(/\\s+/).filter(Boolean);}
async function buildEmbeddings(docs){const r=[];for(let i=0;i<docs.length;i++){const tf={};tokenize(docs[i].text).forEach(t=>{tf[t]=(tf[t]||0)+1;});r.push(tf);if(i%50===0)await new Promise(x=>setTimeout(x,0));}return r;}
function cosine(a,b){let dot=0,mA=0,mB=0;const ks=new Set([...Object.keys(a),...Object.keys(b)]);ks.forEach(k=>{dot+=(a[k]||0)*(b[k]||0);mA+=(a[k]||0)**2;mB+=(b[k]||0)**2;});return(mA===0||mB===0)?0:dot/(Math.sqrt(mA)*Math.sqrt(mB));}
function retrieve(query){const q={};tokenize(query).forEach(t=>{q[t]=(q[t]||0)+1;});return embeddings.map((e,i)=>({index:i,score:cosine(q,e)})).sort((a,b)=>b.score-a.score).slice(0,TOP_K);}

// ── DATA PROCESSING ───────────────────────────────────────────────────────────
function jsonToText(v){if(v===null||v===undefined)return "";if(typeof v==="string")return v;if(typeof v==="number"||typeof v==="boolean")return String(v);if(Array.isArray(v))return v.map(x=>jsonToText(x)).join(" ");if(typeof v==="object")return Object.entries(v).map(([k,x])=>`${k}: ${jsonToText(x)}`).join(" ");return String(v);}
function getRecordLabel(item,index){if(typeof item==="object"&&item!==null){for(const f of["name","title","label","id","key","slug","username","email","subject","description"]){if(item[f]!==undefined&&item[f]!==null&&String(item[f]).trim())return String(item[f]).slice(0,48);}}return `Record ${index+1}`;}
function buildChunks(data){const result=[];if(Array.isArray(data)){data.forEach((item,i)=>result.push({text:jsonToText(item),label:getRecordLabel(item,i),raw:item,index:i}));return result;}if(typeof data==="object"&&data!==null){const entries=Object.entries(data);if(entries.length<=30){entries.forEach(([key,value],i)=>result.push({text:`${key}: ${jsonToText(value)}`,label:key,raw:{[key]:value},index:i}));return result;}}const fullText=typeof data==="string"?data:JSON.stringify(data,null,2),words=fullText.split(/\\s+/);let start=0;while(start<words.length){const end=Math.min(start+CHUNK_SIZE,words.length);result.push({text:words.slice(start,end).join(" "),label:`Chunk ${result.length+1}`,raw:words.slice(start,end).join(" "),index:result.length});if(end>=words.length)break;start+=CHUNK_SIZE-CHUNK_OVERLAP;}return result;}

// ── API CONNECTION ─────────────────────────────────────────────────────────────
async function connectAPI() {
  const urlInput=document.getElementById("apiUrl").value.trim(),auth=document.getElementById("apiAuth").value.trim(),method=document.getElementById("apiMethod").value,body=document.getElementById("apiBody").value.trim(),btn=document.getElementById("connectBtn");
  if(!urlInput){setStatus("Enter an API URL first.","");return;}
  setStatus("Connecting…","loading"); btn.disabled=true;
  try {
    const headers={};
    if(auth){const ci=auth.indexOf(":");if(ci>0&&ci<40){headers[auth.slice(0,ci).trim()]=auth.slice(ci+1).trim();}else{headers["Authorization"]=`Bearer ${auth}`;}}
    const options={method,headers};
    if(method==="POST"&&body){headers["Content-Type"]="application/json";options.body=body;}
    const response=await fetch(urlInput,options);
    if(!response.ok)throw new Error(`HTTP ${response.status} ${response.statusText}`);
    const ct=response.headers.get("content-type")||"";
    let data;
    if(ct.includes("application/json")){data=await response.json();}else{const text=await response.text();try{data=JSON.parse(text);}catch{data=text;}}
    chunks=buildChunks(data);
    embeddings=await buildEmbeddings(chunks);
    let domain;try{domain=new URL(urlInput).hostname;}catch{domain=urlInput;}
    updateSourceName(domain);
    const mt=document.getElementById("sourceMeta");if(mt)mt.textContent=`${chunks.length} records indexed`;
    setStatus(`${chunks.length} records indexed`,"active");
    addMessage("ai",`Connected to **${domain}** — **${chunks.length}** records indexed.\\n\\nAsk me anything about the data.`);
  } catch(err) {
    setStatus(err.message,""); updateSourceName("");
    addMessage("ai",`Connection failed: **${err.message}**\\n\\n- Check the URL and CORS headers.`);
  } finally { btn.disabled=false; }
}

// ── CHAT ───────────────────────────────────────────────────────────────────────
function addMessage(role,text){const chat=document.getElementById("chat"),msg=document.createElement("div");msg.className=`message ${role}`;const bubble=document.createElement("div");bubble.className="bubble";if(text==="__thinking__"){const row=document.createElement("div");row.className="thinking-row";row.innerHTML='<div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div>';bubble.appendChild(row);}else{bubble.replaceChildren(markdownToFragment(text));}msg.appendChild(bubble);chat.appendChild(msg);chat.scrollTop=chat.scrollHeight;return msg;}

async function sendMessage() {
  const input=document.getElementById("input"),query=input.value.trim();
  if(!query)return;
  if(!chunks.length){addMessage("ai","Connect an API endpoint first, then ask questions.");return;}
  input.value=""; input.style.height="52px";
  addMessage("user",query);
  showStop();
  currentController=new AbortController();
  const {signal}=currentController;
  const timeoutId=setTimeout(()=>{if(currentController)currentController.abort("timeout");},TIMEOUT_MS);
  const retrieved=retrieve(query);
  const MAX_CONTEXT_CHARS=3500;
  const context=retrieved.map(r=>{const text=chunks[r.index].text.slice(0,1000);return `[${chunks[r.index].label}]\\n\\n${text}`;}).join("\\n\\n---\\n\\n").slice(0,MAX_CONTEXT_CHARS);
  const apiKey=getApiKey();
  if(!apiKey){addMessage("ai","A Groq API key is required. Reload to enter one.");showSend();clearTimeout(timeoutId);currentController=null;return;}
  const thinkingMsg=addMessage("ai","__thinking__");
  try {
    const response=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${apiKey}`},signal,body:JSON.stringify({model:"llama-3.3-70b-versatile",messages:[{role:"system",content:"You are a data assistant. Answer ONLY from the provided data context. Use concise Markdown. If not in the data say so."},{role:"user",content:`API Data Context:\\n\\n${context}\\n\\nQuestion:\\n${query}`}],temperature:0.2,max_tokens:2048})});
    const data=await response.json();
    thinkingMsg.remove();
    if(!response.ok){addMessage("ai",data.error?.message||"Groq API error.");return;}
    addMessage("ai",data.choices?.[0]?.message?.content||"No response.");
  } catch(err) {
    if(thinkingMsg.isConnected)thinkingMsg.remove();
    if(err.name==="AbortError"||signal.aborted){addMessage("ai",signal.reason==="timeout"?"*Request timed out.*":"*Generation stopped.*");}
    else{addMessage("ai",`Error: **${err.message}**`);}
  } finally { clearTimeout(timeoutId); currentController=null; showSend(); }
}

// ── RECORD VIEWER ──────────────────────────────────────────────────────────────
function openRecord(chunkIndex){const chunk=chunks[chunkIndex];if(!chunk)return;document.getElementById("dataRecordInfo").textContent=chunk.label;document.getElementById("dataContent").textContent=typeof chunk.raw==="object"?JSON.stringify(chunk.raw,null,2):String(chunk.raw);document.getElementById("dataModal").style.display="flex";}
function closeDataViewer(){document.getElementById("dataModal").style.display="none";}
"""

v3_html = build_html(
    nonce_style="cv3-style",
    nonce_script="cv3-script",
    title="API Chatbot — Groq",
    csp_connect="https://api.groq.com http: https:",
    sidebar_html=V3_SIDEBAR,
    topbar_extra="",
    extra_js=V3_JS_CORE,
    pill_text="Groq · Cloud",
    subtitle="Connect any REST endpoint and ask questions about the returned data."
)

with open(r'Chatbot_AI\Chatbot_V3.html', 'w', encoding='utf-8') as f:
    f.write(v3_html)
print("Chatbot_V3.html written:", len(v3_html), "chars")
print("Done!")
