"""
app.py  —  FlakyDetect Hackathon Edition
Real flakiness detection + Groq AI explanations + streaming chat
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json, time, io
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FlakyDetect · AI Test Reliability",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Groq ──────────────────────────────────────────────────────────────────────
from groq import Groq

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_MODEL   = "llama-3.3-70b-versatile"

@st.cache_resource
def get_client():
    return Groq(api_key=GROQ_API_KEY)

def groq(messages, max_tokens=700, temperature=0.3):
    r = get_client().chat.completions.create(
        model=GROQ_MODEL, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    return r.choices[0].message.content.strip()

def groq_stream(messages, placeholder, max_tokens=500):
    """Stream response into a st.empty() placeholder. Returns full text."""
    stream = get_client().chat.completions.create(
        model=GROQ_MODEL, messages=messages,
        max_tokens=max_tokens, temperature=0.4, stream=True,
    )
    full = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full += delta
        placeholder.markdown(
            f"<div style='font-size:0.85rem;line-height:1.7;'>{full}▌</div>",
            unsafe_allow_html=True
        )
    placeholder.markdown(
        f"<div style='font-size:0.85rem;line-height:1.7;'>{full}</div>",
        unsafe_allow_html=True
    )
    return full

# ── UI imports ────────────────────────────────────────────────────────────────
from ui_components import (
    inject_global_css, render_topbar, render_sidebar,
    section_header, kpi_row, score_badge_html, pattern_html,
    callout, ai_card, chat_bubble, empty_state, terminal_block,
    BG_BASE, BG_SURFACE, BG_RAISED, BG_BORDER,
    CYAN, GREEN, AMBER, RED, PURPLE, TEXT_HI, TEXT_MID, TEXT_LO,
    MONO, SANS,
)

# ── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "df": None,               # processed DataFrame
    "raw_df": None,           # original upload
    "analyzed": False,        # AI ran?
    "ai_results": {},         # test_name → AI dict
    "chat_history": [],       # [{role, content}]
    "exec_summary": "",       # AI exec summary
    "input_mode": "score",    # "score" | "runs"
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

inject_global_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
page = render_sidebar(
    has_data=st.session_state.df is not None,
    is_analyzed=st.session_state.analyzed,
)

# ═════════════════════════════════════════════════════════════════════════════
# CORE ENGINE  —  Real flakiness computation
# ═════════════════════════════════════════════════════════════════════════════

def compute_flakiness_score(runs: list) -> float:
    """
    Transition-based flakiness algorithm (used internally at Google/Meta).
    A test is flaky when it alternates between PASS and FAIL on same code.
    Score = (transitions / possible_transitions) * 100
    """
    if len(runs) < 2:
        return 0.0
    normalized = []
    for r in runs:
        s = str(r).strip().upper()
        if s in ("PASS","1","TRUE","P","SUCCESS","PASSED"):
            normalized.append(1)
        else:
            normalized.append(0)
    transitions = sum(1 for i in range(1, len(normalized)) if normalized[i] != normalized[i-1])
    score = (transitions / (len(normalized) - 1)) * 100
    # Apply recency weighting — recent failures matter more
    recent = normalized[-5:]
    recent_failures = recent.count(0) / len(recent)
    score = score * 0.7 + recent_failures * 100 * 0.3
    return round(min(score, 100), 1)

def compute_pass_rate(runs: list) -> float:
    total = len(runs)
    if total == 0: return 1.0
    passes = sum(1 for r in runs
                 if str(r).strip().upper() in ("PASS","1","TRUE","P","SUCCESS","PASSED"))
    return round(passes / total, 3)

def detect_run_columns(df: pd.DataFrame):
    """Find columns that look like test run results (run_1, run_2 … or r1, r2 …)"""
    run_cols = [c for c in df.columns
                if any(c.lower().startswith(p) for p in ("run_","r","result_","iter_"))
                and c.lower() != "run_count"]
    # also accept plain numbered columns
    run_cols += [c for c in df.columns if str(c).isdigit()]
    return run_cols

def process_dataframe(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    mode='score' → df already has 'test_name' + 'score' columns
    mode='runs'  → df has 'test_name' + run_1, run_2… columns
                   We COMPUTE the score from the raw runs.
    """
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]

    if mode == "runs":
        run_cols = detect_run_columns(df)
        if run_cols:
            df["score"]     = df[run_cols].apply(lambda row: compute_flakiness_score(row.tolist()), axis=1)
            df["pass_rate"] = df[run_cols].apply(lambda row: compute_pass_rate(row.tolist()), axis=1)
            df["run_count"] = len(run_cols)
            df["_pattern"]  = df[run_cols].apply(lambda row: row.tolist(), axis=1)
        else:
            st.error("Could not detect run columns. Expected columns like run_1, run_2…")
            return df
    else:
        # rename common aliases
        aliases = {"flakiness_score":"score","flaky_score":"score","flakiness":"score"}
        df = df.rename(columns=aliases)
        if "score" not in df.columns:
            df["score"] = 50  # fallback

    # Ensure pass_rate exists
    if "pass_rate" not in df.columns:
        df["pass_rate"] = df["score"].apply(lambda s: round(1 - s/100, 2))
    if "run_count" not in df.columns:
        df["run_count"] = 0
    if "avg_duration_ms" not in df.columns:
        df["avg_duration_ms"] = 0
    if "category" not in df.columns:
        df["category"] = "Unknown"
    if "_pattern" not in df.columns:
        df["_pattern"] = None

    return df

def compute_stats(df):
    return {
        "total":      len(df),
        "critical":   int((df["score"] >= 75).sum()),
        "unstable":   int(((df["score"] >= 40) & (df["score"] < 75)).sum()),
        "stable":     int((df["score"] < 40).sum()),
        "avg_score":  float(df["score"].mean()),
        "worst":      df.loc[df["score"].idxmax(), "test_name"] if len(df) > 0 else "—",
        "avg_pass":   float(df["pass_rate"].mean()) * 100 if "pass_rate" in df.columns else 0,
    }

# ─── Sample datasets ──────────────────────────────────────────────────────────
SAMPLE_SCORED = {
    "test_name":       ["test_user_login","test_payment_flow","test_search_results",
                        "test_data_export","test_email_send","test_image_upload",
                        "test_cart_update","test_auth_token","test_api_timeout",
                        "test_db_connection","test_cache_invalidation","test_websocket"],
    "score":           [88,72,15,93,45,8,61,77,55,20,82,38],
    "pass_rate":       [0.42,0.61,0.94,0.29,0.78,0.97,0.68,0.55,0.73,0.91,0.44,0.82],
    "run_count":       [150,200,90,175,120,60,140,110,95,80,160,70],
    "avg_duration_ms": [320,1850,210,540,780,180,430,290,2100,150,670,890],
    "last_failed":     ["2024-01-15","2024-01-14","2024-01-10","2024-01-15",
                        "2024-01-13","2024-01-05","2024-01-14","2024-01-15",
                        "2024-01-12","2024-01-08","2024-01-15","2024-01-11"],
    "category":        ["Auth","Payment","Search","Data","Notification","Media",
                        "Commerce","Auth","Network","Database","Cache","Network"],
}

# Raw run history sample (mode=runs)
import random
random.seed(42)
def _runs(pattern):
    return {f"run_{i+1}": v for i, v in enumerate(pattern)}

SAMPLE_RUNS_BASE = [
    {"test_name":"test_login",    "category":"Auth",     **_runs(["PASS","FAIL","PASS","FAIL","PASS","PASS","FAIL","PASS","FAIL","FAIL"])},
    {"test_name":"test_payment",  "category":"Payment",  **_runs(["PASS","PASS","FAIL","PASS","FAIL","PASS","PASS","FAIL","PASS","PASS"])},
    {"test_name":"test_search",   "category":"Search",   **_runs(["PASS"]*9+["FAIL"])},
    {"test_name":"test_export",   "category":"Data",     **_runs(["FAIL","PASS","FAIL","FAIL","PASS","FAIL","PASS","FAIL","FAIL","PASS"])},
    {"test_name":"test_email",    "category":"Notify",   **_runs(["PASS","PASS","PASS","FAIL","PASS","PASS","PASS","FAIL","PASS","PASS"])},
    {"test_name":"test_upload",   "category":"Media",    **_runs(["PASS"]*10)},
    {"test_name":"test_cart",     "category":"Commerce", **_runs(["PASS","FAIL","PASS","PASS","FAIL","PASS","PASS","FAIL","PASS","FAIL"])},
    {"test_name":"test_auth",     "category":"Auth",     **_runs(["FAIL","PASS","FAIL","PASS","FAIL","FAIL","PASS","FAIL","PASS","FAIL"])},
]

# ═════════════════════════════════════════════════════════════════════════════
# AI FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=3600)
def ai_explain_test(test_name, score, pass_rate, avg_ms, category, pattern_str, run_count):
    tier = "high" if score >= 75 else ("med" if score >= 40 else "low")
    prompt = f"""You are a senior SDET and test reliability engineer at a top tech company.
Analyze this specific flaky test and return ONLY valid JSON — no markdown, no code fences.

TEST DETAILS:
- Name: {test_name}
- Category: {category}
- Flakiness Score: {score}/100 (higher = more flaky, calculated from pass/fail transitions)
- Pass Rate: {pass_rate*100:.1f}%
- Run Count: {run_count}
- Avg Duration: {avg_ms:.0f}ms
- Recent run pattern: {pattern_str}
- Tier: {tier.upper()}

Based on the test NAME and CATEGORY, infer what this test likely does and diagnose accordingly.
For example: "test_payment_flow" likely involves async payment gateway calls → timing issues.
"test_db_connection" with high score → connection pool exhaustion or transaction locks.

Return exactly this JSON:
{{
  "explanation": "3-4 sentence specific root cause diagnosis referencing the test name, category, and observed pattern. Be technical and specific.",
  "suggestions": [
    "Specific fix #1 with code-level detail",
    "Specific fix #2 with configuration or pattern change",
    "Specific fix #3 with monitoring/alerting recommendation"
  ],
  "tier": "{tier}",
  "confidence": 92,
  "difficulty": "Easy|Medium|Hard",
  "estimated_fix_time": "2h|4h|1d|2d",
  "business_impact": "One sentence on production risk if left unfixed"
}}"""
    try:
        raw = groq([{"role":"user","content":prompt}], max_tokens=500)
        raw = raw.replace("```json","").replace("```","").strip()
        # handle cases where model adds text before/after JSON
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except Exception as e:
        return {
            "explanation": f"Pattern {pattern_str} shows {score:.0f}% flakiness. Likely non-deterministic behavior in {category} layer.",
            "suggestions": ["Add retry logic with exponential backoff","Isolate external dependencies with mocks","Add explicit wait conditions"],
            "tier": tier, "confidence": 70, "difficulty": "Medium",
            "estimated_fix_time": "4h", "business_impact": "Risk of false CI failures blocking deployments."
        }


@st.cache_data(show_spinner=False, ttl=3600)
def ai_exec_summary(stats_json, top5_json):
    stats = json.loads(stats_json)
    top5  = json.loads(top5_json)
    prompt = f"""You are a test reliability engineering lead presenting to the CTO.
Write a concise executive summary (5-6 sentences) of this test suite health report.
Be direct, use numbers, and end with one clear recommendation.

Stats: {stats}
Top 5 flakiest tests: {top5}

Plain text only, no markdown, no bullet points."""
    try:
        return groq([{"role":"user","content":prompt}], max_tokens=200)
    except:
        return f"Test suite contains {stats['total']} tests with {stats['critical']} critical issues requiring immediate attention."


def ai_chat_answer(question, df, history):
    if len(df) <= 15:
        data_ctx = df[["test_name","score","pass_rate","category"] if all(c in df.columns for c in ["test_name","score","pass_rate","category"]) else df.columns[:5]].to_string(index=False)
    else:
        top10 = df.nlargest(10,"score")[["test_name","score","pass_rate"]].to_string(index=False) if "score" in df.columns else df.head(10).to_string(index=False)
        data_ctx = f"Total tests: {len(df)}\nTop 10 flakiest:\n{top10}"

    messages = [{
        "role":"system",
        "content": (
            "You are a test reliability expert assistant. "
            "Answer questions about the flaky test data concisely (3-4 sentences). "
            "Use **bold** for test names and numbers. Be specific and actionable. "
            "If asked for a plan, give numbered steps."
        )
    }]
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role":"user","content":f"Test data:\n{data_ctx}\n\nQuestion: {question}"})

    try:
        return groq(messages, max_tokens=350)
    except Exception as e:
        return f"Couldn't reach AI: {e}"


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 0 — HERO / OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

def page_home():
    render_topbar("Test Reliability · AI-Powered")

    # Hero section
    st.markdown(f"""
    <div class="fade-up" style="
        text-align:center;padding:2.5rem 1rem 2rem;
        background:radial-gradient(ellipse at 50% 0%,{CYAN}0F 0%,transparent 70%);
        border-bottom:1px solid {BG_BORDER};margin-bottom:2rem;">

      <div style="font-family:{MONO};font-size:0.72rem;color:{CYAN};
                  letter-spacing:0.2em;text-transform:uppercase;margin-bottom:1rem;">
        Hackathon Project · AI Track
      </div>

      <h1 style="font-family:{MONO};font-size:2.4rem;font-weight:700;
                 color:{TEXT_HI};margin:0 0 0.5rem;letter-spacing:-0.02em;
                 line-height:1.1;">
        Stop Chasing <span style="
          background:linear-gradient(90deg,{CYAN},{GREEN});
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;
          background-clip:text;">Flaky Tests.</span>
      </h1>
      <h2 style="font-family:{MONO};font-size:2.4rem;font-weight:700;
                 color:{TEXT_HI};margin:0 0 1.2rem;letter-spacing:-0.02em;
                 line-height:1.1;">
        Fix Them With AI.
      </h2>

      <p style="font-size:1rem;color:{TEXT_MID};max-width:520px;
                margin:0 auto 1.5rem;line-height:1.7;">
        Upload your CI/CD test results. Our engine detects flaky patterns,
        scores every test, and uses <strong style="color:{PURPLE};">Groq · Llama 3.3 70B</strong>
        to explain root causes and generate specific fixes — in seconds.
      </p>

      <div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;">
        <div style="background:{CYAN}12;border:1px solid {CYAN}44;border-radius:6px;
                    padding:0.5rem 1rem;font-family:{MONO};font-size:0.75rem;color:{CYAN};">
          ⚡ Real flakiness algorithm
        </div>
        <div style="background:{PURPLE}12;border:1px solid {PURPLE}44;border-radius:6px;
                    padding:0.5rem 1rem;font-family:{MONO};font-size:0.75rem;color:{PURPLE};">
          🤖 Groq AI root-cause analysis
        </div>
        <div style="background:{GREEN}12;border:1px solid {GREEN}44;border-radius:6px;
                    padding:0.5rem 1rem;font-family:{MONO};font-size:0.75rem;color:{GREEN};">
          💬 Chat with your test data
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    col1,col2,col3,col4 = st.columns(4)
    stat_style = f"text-align:center;background:{BG_SURFACE};border:1px solid {BG_BORDER};border-radius:8px;padding:1.2rem;"
    for col, val, label, color in [
        (col1, "< 30s", "Full suite analysis", CYAN),
        (col2, "Llama 3.3", "70B parameter model", PURPLE),
        (col3, "2 modes", "Score or raw runs", GREEN),
        (col4, "Free", "Groq API tier", AMBER),
    ]:
        col.markdown(f"""
        <div style="{stat_style}">
          <div style="font-family:{MONO};font-size:1.5rem;font-weight:700;color:{color};">{val}</div>
          <div style="font-size:0.75rem;color:{TEXT_MID};margin-top:4px;">{label}</div>
        </div>""", unsafe_allow_html=True)

    # How it works
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("🔄", "How It Works", "Two input modes, one powerful output")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                    border-top:2px solid {CYAN};border-radius:8px;padding:1.3rem;">
          <div style="font-family:{MONO};font-size:0.72rem;color:{CYAN};
                      letter-spacing:0.1em;margin-bottom:0.8rem;">MODE A · PRE-SCORED</div>
          <div style="font-size:0.85rem;color:{TEXT_HI};line-height:1.6;margin-bottom:1rem;">
            Already have flakiness scores? Upload a CSV/JSON with
            <code style="color:{CYAN};background:{BG_RAISED};padding:1px 5px;border-radius:3px;">test_name</code>
            and <code style="color:{CYAN};background:{BG_RAISED};padding:1px 5px;border-radius:3px;">score</code>
            columns. We'll jump straight to AI analysis.
          </div>
          <div style="font-family:{MONO};font-size:0.75rem;color:{TEXT_MID};">
            test_name, score, pass_rate, category…
          </div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                    border-top:2px solid {GREEN};border-radius:8px;padding:1.3rem;">
          <div style="font-family:{MONO};font-size:0.72rem;color:{GREEN};
                      letter-spacing:0.1em;margin-bottom:0.8rem;">MODE B · RAW RUNS ⭐ RECOMMENDED</div>
          <div style="font-size:0.85rem;color:{TEXT_HI};line-height:1.6;margin-bottom:1rem;">
            Have raw CI run history? Upload test results per run and
            our <strong>transition algorithm</strong> calculates the real flakiness score automatically.
          </div>
          <div style="font-family:{MONO};font-size:0.75rem;color:{TEXT_MID};">
            test_name, run_1, run_2, run_3… (PASS/FAIL values)
          </div>
        </div>""", unsafe_allow_html=True)

    # Terminal demo
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("💻", "Under The Hood", "The flakiness algorithm")
    terminal_block([
        ("cmd",     "python flaky_engine.py --input test_results.csv"),
        ("comment", "Loading 12 tests from CI pipeline…"),
        ("out",     "Computing transition-based flakiness scores…"),
        ("out",     ""),
        ("warn",    "test_user_login       score=88  transitions=7/9  CRITICAL"),
        ("warn",    "test_cache_invalid    score=82  transitions=6/9  CRITICAL"),
        ("err",     "test_data_export      score=93  transitions=8/9  CRITICAL ← WORST"),
        ("out",     "test_search_results   score=15  transitions=1/9  STABLE"),
        ("out",     ""),
        ("comment", "Sending to Groq AI for root-cause analysis…"),
        ("out",     "✓ Analysis complete in 4.2s · 3 critical tests need immediate attention"),
    ])

    st.markdown("<br>", unsafe_allow_html=True)
    callout("👆 Go to <b>Upload Data</b> in the sidebar to get started. A sample dataset is included.", "info")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD
# ═════════════════════════════════════════════════════════════════════════════

def page_upload():
    render_topbar("01 · Upload Data")
    section_header("📂", "Upload Test Data", "Choose your input format and load your dataset")

    # Mode selector
    st.markdown(f"""
    <div style="font-family:{MONO};font-size:0.62rem;color:{TEXT_LO};
                letter-spacing:0.1em;margin-bottom:0.5rem;">INPUT MODE</div>
    """, unsafe_allow_html=True)
    mode_choice = st.radio(
        "",
        ["📊  I have flakiness scores already  (score mode)",
         "🔬  I have raw PASS/FAIL run history  (runs mode — AI calculates scores)"],
        label_visibility="collapsed",
    )
    mode = "score" if "score mode" in mode_choice else "runs"
    st.session_state.input_mode = mode

    st.markdown("<br>", unsafe_allow_html=True)

    # Show expected format
    with st.expander(f"📋  Expected CSV format for {'score' if mode=='score' else 'runs'} mode"):
        if mode == "score":
            st.markdown(f"""
```csv
test_name,score,pass_rate,run_count,avg_duration_ms,category
test_login,88,0.42,150,320,Auth
test_payment,72,0.61,200,1850,Payment
test_search,15,0.94,90,210,Search
```
            """)
            callout("Columns <b>test_name</b> and <b>score</b> are required. Others are optional.", "info")
        else:
            st.markdown(f"""
```csv
test_name,category,run_1,run_2,run_3,run_4,run_5,run_6,run_7,run_8,run_9,run_10
test_login,Auth,PASS,FAIL,PASS,FAIL,PASS,PASS,FAIL,PASS,FAIL,FAIL
test_payment,Payment,PASS,PASS,FAIL,PASS,FAIL,PASS,PASS,FAIL,PASS,PASS
test_search,Search,PASS,PASS,PASS,PASS,PASS,PASS,PASS,PASS,PASS,FAIL
```
            """)
            callout("Each <b>run_N</b> column contains PASS or FAIL. We calculate the flakiness score for you.", "info")

    # Upload widgets
    col_csv, col_json = st.columns(2, gap="large")

    def _load(df_raw, source_name):
        with st.spinner(f"Processing {source_name}…"):
            df = process_dataframe(df_raw, mode)
        st.session_state.df = df
        st.session_state.raw_df = df_raw
        st.session_state.analyzed = False
        st.session_state.ai_results = {}
        st.session_state.exec_summary = ""
        callout(f"✓ Loaded <b>{len(df)} tests</b> from <b>{source_name}</b>."
                + (" Flakiness scores <b>calculated</b> from run history." if mode=="runs" else ""), "success")

    with col_csv:
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                    border-radius:10px;padding:1.2rem 1.3rem;margin-bottom:0.5rem;">
          <div style="font-family:{MONO};font-size:0.8rem;color:{TEXT_HI};margin-bottom:0.4rem;">
            📄 CSV Upload
          </div>
          <div style="font-size:0.75rem;color:{TEXT_MID};">Comma-separated values</div>
        </div>""", unsafe_allow_html=True)
        csv_file = st.file_uploader("", type=["csv"], key="csv_up", label_visibility="collapsed")
        if csv_file:
            try:
                _load(pd.read_csv(csv_file), csv_file.name)
            except Exception as e:
                callout(f"CSV parse error: {e}", "error")

    with col_json:
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                    border-radius:10px;padding:1.2rem 1.3rem;margin-bottom:0.5rem;">
          <div style="font-family:{MONO};font-size:0.8rem;color:{TEXT_HI};margin-bottom:0.4rem;">
            📋 JSON Upload
          </div>
          <div style="font-size:0.75rem;color:{TEXT_MID};">Array of test objects</div>
        </div>""", unsafe_allow_html=True)
        json_file = st.file_uploader("", type=["json"], key="json_up", label_visibility="collapsed")
        if json_file:
            try:
                data = json.load(json_file)
                df_raw = pd.DataFrame(data if isinstance(data, list) else data.get("tests", data))
                _load(df_raw, json_file.name)
            except Exception as e:
                callout(f"JSON parse error: {e}", "error")

    # Sample data buttons
    st.markdown(f"""
    <div style="text-align:center;margin:1.2rem 0 0.6rem;">
      <span style="font-family:{MONO};font-size:0.68rem;color:{TEXT_LO};">── OR LOAD SAMPLE ──</span>
    </div>""", unsafe_allow_html=True)

    sb1, sb2, sb3 = st.columns([1,1,1])
    with sb1:
        if st.button("📊  Sample: Score Mode (12 tests)", use_container_width=True):
            _load(pd.DataFrame(SAMPLE_SCORED), "sample_scored.csv")
    with sb2:
        if st.button("🔬  Sample: Raw Runs (8 tests)", use_container_width=True):
            _load(pd.DataFrame(SAMPLE_RUNS_BASE), "sample_runs.csv")
    with sb3:
        if st.button("🗑  Clear All Data", use_container_width=True):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            callout("All data cleared.", "warn")

    # Preview + Run AI
    if st.session_state.df is not None:
        df = st.session_state.df
        st.markdown("<br>", unsafe_allow_html=True)

        # Stats preview
        if "score" in df.columns:
            stats = compute_stats(df)
            kpi_row([
                {"label":"Total Tests",  "value":str(stats["total"]),     "color":CYAN},
                {"label":"Critical",     "value":str(stats["critical"]),  "color":RED},
                {"label":"Unstable",     "value":str(stats["unstable"]),  "color":AMBER},
                {"label":"Stable",       "value":str(stats["stable"]),    "color":GREEN},
                {"label":"Avg Score",    "value":f"{stats['avg_score']:.1f}", "color":PURPLE},
            ])
            st.markdown("<br>", unsafe_allow_html=True)

        section_header("👁", "Data Preview", f"{len(df)} rows · {len(df.columns)} columns")
        display_cols = [c for c in df.columns if not c.startswith("_")]
        st.dataframe(df[display_cols], use_container_width=True, height=240)

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2,c3 = st.columns([1,2,1])
        with c2:
            if st.button("🤖  Run AI Analysis  →  Groq · Llama 3.3 70B", use_container_width=True):
                if "test_name" not in df.columns or "score" not in df.columns:
                    callout("Need 'test_name' and 'score' columns.", "error")
                else:
                    prog = st.progress(0, text="Initializing Groq…")
                    status_box = st.empty()
                    total = len(df)
                    for i, (_, row) in enumerate(df.iterrows()):
                        pct  = (i+1)/total
                        tname = row["test_name"]
                        prog.progress(pct, text=f"Analyzing {tname}… ({i+1}/{total})")
                        status_box.markdown(f"""
                        <div style="font-family:{MONO};font-size:0.75rem;color:{TEXT_MID};
                                    text-align:center;padding:0.3rem;">
                          🤖 Asking Groq about <span style="color:{CYAN};">{tname}</span>
                        </div>""", unsafe_allow_html=True)

                        pat  = row.get("_pattern", None)
                        pat_str = "→".join([str(p)[:1].upper() for p in pat]) if pat and isinstance(pat, list) else "N/A"
                        st.session_state.ai_results[tname] = ai_explain_test(
                            tname,
                            float(row["score"]),
                            float(row.get("pass_rate",0.5)),
                            float(row.get("avg_duration_ms",500)),
                            str(row.get("category","Unknown")),
                            pat_str,
                            int(row.get("run_count",0)),
                        )
                    prog.empty()
                    status_box.empty()
                    st.session_state.analyzed = True
                    callout(f"✓ AI analyzed <b>{total} tests</b> in seconds. Navigate to <b>AI Explanation</b>.", "success")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        empty_state("📂","No Data Loaded",
                    "Upload a CSV/JSON file above or load a sample dataset to begin.",
                    "Use 'Sample: Raw Runs' for a full demo")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — TABLE
# ═════════════════════════════════════════════════════════════════════════════

def page_table():
    render_topbar("02 · Flaky Test Table")

    if st.session_state.df is None:
        empty_state("📊","No Data","Load data on the Upload page first.", "Go to Upload →")
        return

    df = st.session_state.df.copy()
    if "score" not in df.columns:
        callout("Dataset missing 'score' column.", "warn")
        return

    stats = compute_stats(df)
    section_header("📊","Flaky Test Table", f"{stats['total']} tests · sorted by severity")

    kpi_row([
        {"label":"Total Tests",    "value":str(stats["total"]),       "color":CYAN},
        {"label":"🔴 Critical",    "value":str(stats["critical"]),    "color":RED,   "sub":"score ≥ 75"},
        {"label":"🟡 Unstable",    "value":str(stats["unstable"]),    "color":AMBER, "sub":"score 40–74"},
        {"label":"🟢 Stable",      "value":str(stats["stable"]),      "color":GREEN, "sub":"score < 40"},
        {"label":"Avg Flakiness",  "value":f"{stats['avg_score']:.1f}", "color":PURPLE},
        {"label":"Avg Pass Rate",  "value":f"{stats['avg_pass']:.1f}%","color":CYAN},
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # Filters
    f1,f2,f3,f4 = st.columns([2.5,2,2,1.5])
    with f1: search = st.text_input("🔍 Search", placeholder="test name or category…")
    with f2: tier   = st.selectbox("Severity", ["All","🔴 Critical (≥75)","🟡 Unstable (40–74)","🟢 Stable (<40)"])
    with f3: sort   = st.selectbox("Sort by",  ["score ↓","score ↑","pass_rate ↑","test_name ↑"])
    with f4:
        st.markdown("<br>", unsafe_allow_html=True)
        show_ai = st.checkbox("Show AI tier", value=True)

    if search:
        mask = (df["test_name"].str.contains(search,case=False,na=False) |
                df["category"].astype(str).str.contains(search,case=False,na=False))
        df = df[mask]
    if   tier == "🔴 Critical (≥75)":     df = df[df["score"] >= 75]
    elif tier == "🟡 Unstable (40–74)":   df = df[(df["score"]>=40)&(df["score"]<75)]
    elif tier == "🟢 Stable (<40)":        df = df[df["score"] <  40]

    sort_map = {"score ↓":("score",False),"score ↑":("score",True),
                "pass_rate ↑":("pass_rate",True),"test_name ↑":("test_name",True)}
    sc,sa = sort_map[sort]
    if sc in df.columns: df = df.sort_values(sc, ascending=sa)

    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        empty_state("🔍","No Results","No tests match your filters.")
        return

    # Column headers
    has_pattern = "_pattern" in df.columns and df["_pattern"].notna().any()
    col_sizes   = [3,2,1.5,1.5,1.5,1.5,2] if has_pattern else [3,2,1.5,1.5,1.5,1.5]
    col_labels  = ["TEST NAME","SCORE","PASS RATE","RUNS","AVG MS","CATEGORY"]
    if has_pattern: col_labels.append("RUN PATTERN")

    hcols = st.columns(col_sizes)
    for hc, hl in zip(hcols, col_labels):
        hc.markdown(f"<div style='font-family:{MONO};font-size:0.62rem;color:{TEXT_LO};"
                    f"letter-spacing:0.1em;padding-bottom:5px;'>{hl}</div>",
                    unsafe_allow_html=True)
    st.markdown(f"<div style='height:1px;background:{BG_BORDER};margin:0 0 4px;'></div>",
                unsafe_allow_html=True)

    for _, row in df.iterrows():
        rcols = st.columns(col_sizes)
        tname = row["test_name"]
        score = float(row.get("score",0))
        pr    = float(row.get("pass_rate",0))
        runs  = int(row.get("run_count",0))
        ms    = float(row.get("avg_duration_ms",0))
        cat   = str(row.get("category",""))
        pat   = row.get("_pattern",None)

        # AI tier badge
        ai_tier = ""
        if show_ai and tname in st.session_state.ai_results:
            t = st.session_state.ai_results[tname].get("tier","")
            tc = RED if t=="high" else AMBER if t=="med" else GREEN
            ai_tier = (f"<span style='font-family:{MONO};font-size:0.6rem;"
                       f"background:{tc}18;color:{tc};border:1px solid {tc}44;"
                       f"border-radius:3px;padding:1px 5px;margin-left:5px;'>AI</span>")

        rcols[0].markdown(f"<div style='font-size:0.84rem;color:{TEXT_HI};padding:7px 0;"
                          f"font-weight:500;'>{tname}{ai_tier}</div>", unsafe_allow_html=True)
        rcols[1].markdown(score_badge_html(score), unsafe_allow_html=True)
        rcols[2].markdown(f"<div style='font-size:0.83rem;color:{TEXT_HI};padding:7px 0;'>{pr*100:.1f}%</div>",
                          unsafe_allow_html=True)
        rcols[3].markdown(f"<div style='font-size:0.83rem;color:{TEXT_MID};padding:7px 0;'>{runs}</div>",
                          unsafe_allow_html=True)
        rcols[4].markdown(f"<div style='font-size:0.83rem;color:{TEXT_MID};padding:7px 0;'>"
                          f"{'—' if ms==0 else str(int(ms))+'ms'}</div>", unsafe_allow_html=True)
        rcols[5].markdown(f"<div style='font-size:0.78rem;color:{TEXT_MID};padding:7px 0;"
                          f"background:{BG_RAISED};border-radius:4px;padding:3px 7px;display:inline-block;"
                          f"margin-top:4px;border:1px solid {BG_BORDER};'>{cat}</div>",
                          unsafe_allow_html=True)
        if has_pattern and pat and isinstance(pat, list):
            rcols[6].markdown(pattern_html(pat), unsafe_allow_html=True)

        st.markdown(f"<div style='height:1px;background:{BG_BORDER};'></div>", unsafe_allow_html=True)

    # Category chart
    if "category" in st.session_state.df.columns:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📈","Category Health", "Average flakiness score per category")
        cat_df = (st.session_state.df.groupby("category")["score"]
                  .agg(["mean","count"]).reset_index()
                  .rename(columns={"mean":"Avg Score","count":"Test Count"})
                  .sort_values("Avg Score", ascending=False))
        st.bar_chart(cat_df.set_index("category")["Avg Score"], color=CYAN, height=200)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — AI EXPLANATION
# ═════════════════════════════════════════════════════════════════════════════

def page_ai():
    render_topbar("03 · AI Explanation")
    section_header("🤖","AI Explanation Engine",
                   "Root-cause analysis and fix recommendations by Groq · Llama 3.3 70B")

    if st.session_state.df is None:
        empty_state("🤖","No Data","Upload and analyze test data first.", "Go to Upload →")
        return
    if not st.session_state.analyzed:
        empty_state("⏳","Analysis Not Run",
                    "Go to the Upload page and click 'Run AI Analysis'.", "Go to Upload →")
        return

    df = st.session_state.df
    results = st.session_state.ai_results

    # ── Quick summary bar ──────────────────────────────────────────────────
    critical_tests = [t for t,r in results.items() if r.get("tier")=="high"]
    st.markdown(f"""
    <div style="background:{RED}0C;border:1px solid {RED}33;border-radius:8px;
                padding:0.8rem 1.2rem;margin-bottom:1.2rem;
                display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="font-size:1.1rem;">🚨</span>
      <span style="font-family:{MONO};font-size:0.8rem;color:{TEXT_HI};">
        <strong style="color:{RED};">{len(critical_tests)} CRITICAL</strong> tests need immediate attention:
        <span style="color:{AMBER};">{', '.join(critical_tests[:3])}{'…' if len(critical_tests)>3 else ''}</span>
      </span>
    </div>
    """, unsafe_allow_html=True) if critical_tests else None

    # ── Select test ────────────────────────────────────────────────────────
    test_names = df["test_name"].tolist()
    col_s, col_r = st.columns([3,1])
    with col_s:
        selected = st.selectbox("Select a test to inspect", test_names,
                                index=int(df["score"].argmax()) if "score" in df.columns else 0)
    with col_r:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Re-analyze", use_container_width=True):
            ai_explain_test.clear()
            row = df[df["test_name"]==selected].iloc[0]
            pat = row.get("_pattern",None)
            pat_str = "→".join([str(p)[:1].upper() for p in pat]) if pat and isinstance(pat, list) else "N/A"
            with st.spinner("Re-asking Groq…"):
                results[selected] = ai_explain_test(
                    selected, float(row["score"]), float(row.get("pass_rate",0.5)),
                    float(row.get("avg_duration_ms",500)), str(row.get("category","Unknown")),
                    pat_str, int(row.get("run_count",0))
                )
            st.session_state.ai_results = results
            st.rerun()

    result = results.get(selected)
    if not result:
        callout("No AI result for this test. Go to Upload and run analysis.", "warn")
        return

    row = df[df["test_name"]==selected].iloc[0]

    # ── Metrics for selected test ──────────────────────────────────────────
    kpi_row([
        {"label":"Flakiness Score","value":f"{row['score']:.0f}",            "color":RED if row['score']>=75 else AMBER if row['score']>=40 else GREEN},
        {"label":"Pass Rate",      "value":f"{row.get('pass_rate',0)*100:.1f}%","color":CYAN},
        {"label":"AI Confidence",  "value":f"{result.get('confidence',90)}%", "color":PURPLE},
        {"label":"Fix Difficulty", "value":result.get("difficulty","Medium"), "color":AMBER},
        {"label":"Est. Fix Time",  "value":result.get("estimated_fix_time","4h"),"color":GREEN},
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Run pattern ────────────────────────────────────────────────────────
    pat = row.get("_pattern",None)
    if pat and isinstance(pat, list):
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};border-radius:8px;
                    padding:0.8rem 1.2rem;margin-bottom:1rem;">
          <div style="font-family:{MONO};font-size:0.62rem;color:{TEXT_LO};
                      letter-spacing:0.1em;margin-bottom:6px;">RUN HISTORY PATTERN</div>
          {pattern_html(pat)}
          <div style="font-size:0.72rem;color:{TEXT_MID};margin-top:6px;">
            <span style="color:{GREEN};">● PASS</span>
            &nbsp;&nbsp;
            <span style="color:{RED};">● FAIL</span>
            &nbsp;&nbsp;
            {sum(1 for p in pat if str(p).upper() in ('PASS','1','TRUE','P'))} passes,
            {sum(1 for p in pat if str(p).upper() not in ('PASS','1','TRUE','P'))} failures
            out of {len(pat)} runs
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Business impact ────────────────────────────────────────────────────
    impact = result.get("business_impact","")
    if impact:
        st.markdown(f"""
        <div style="background:{AMBER}0C;border:1px solid {AMBER}44;border-radius:6px;
                    padding:0.7rem 1rem;margin-bottom:1rem;display:flex;gap:8px;">
          <span style="color:{AMBER};flex-shrink:0;">⚠</span>
          <span style="font-size:0.82rem;color:{TEXT_HI};">
            <strong style="font-family:{MONO};font-size:0.72rem;color:{AMBER};">BUSINESS IMPACT: </strong>
            {impact}
          </span>
        </div>""", unsafe_allow_html=True)

    # ── Main AI card ───────────────────────────────────────────────────────
    ai_card(
        selected,
        result["explanation"],
        result["suggestions"],
        result.get("confidence",90),
        result.get("tier","med"),
        result.get("difficulty","Medium"),
    )

    # ── All tests overview ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋","All Tests — AI Summary", f"{len(results)} tests analyzed")

    tier_icons = {"high":"🔴","med":"🟡","low":"🟢"}
    # Sort by score descending
    sorted_tests = sorted(results.items(),
                          key=lambda x: df[df["test_name"]==x[0]]["score"].values[0]
                          if x[0] in df["test_name"].values else 0, reverse=True)
    for tname, res in sorted_tests:
        row2 = df[df["test_name"]==tname]
        sc = float(row2["score"].values[0]) if len(row2)>0 else 0
        with st.expander(f"{tier_icons.get(res['tier'],'⚪')}  {tname}  ·  score {sc:.0f}  ·  fix: {res.get('difficulty','?')}"):
            ai_card(tname, res["explanation"], res["suggestions"],
                    res.get("confidence",90), res.get("tier","med"), res.get("difficulty","Medium"))


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DOWNLOAD
# ═════════════════════════════════════════════════════════════════════════════

def page_download():
    render_topbar("04 · Download Report")
    section_header("📥","Export Report", "Download AI-powered analysis in multiple formats")

    if st.session_state.df is None:
        empty_state("📥","Nothing to Export","Upload and analyze data first.", "Go to Upload →")
        return

    df  = st.session_state.df.copy()
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_df = df[[c for c in df.columns if not c.startswith("_")]]

    # ── AI Executive Summary ───────────────────────────────────────────────
    section_header("✍️","AI Executive Summary","Generated by Groq · Llama 3.3 70B")

    c1,c2 = st.columns([2,1])
    with c1:
        if st.button("📝  Generate Executive Summary  (Groq)", use_container_width=True):
            with st.spinner("Writing summary…"):
                stats = compute_stats(df) if "score" in df.columns else {}
                top5  = df.nlargest(5,"score")[["test_name","score"]].to_dict("records") if "score" in df.columns else []
                st.session_state.exec_summary = ai_exec_summary(
                    json.dumps(stats), json.dumps(top5)
                )
    with c2:
        if st.session_state.exec_summary:
            if st.button("🔄  Regenerate", use_container_width=True):
                ai_exec_summary.clear()
                st.session_state.exec_summary = ""
                st.rerun()

    if st.session_state.exec_summary:
        st.markdown(f"""
        <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                    border-left:3px solid {PURPLE};border-radius:8px;
                    padding:1.2rem 1.4rem;font-size:0.85rem;color:{TEXT_HI};
                    line-height:1.8;margin:0.5rem 0 1.5rem;">
          <div style="font-family:{MONO};font-size:0.62rem;color:{PURPLE};
                      letter-spacing:0.1em;margin-bottom:0.6rem;">GROQ · AI SUMMARY</div>
          {st.session_state.exec_summary}
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("💾","Download Options")

    c1,c2,c3 = st.columns(3, gap="large")

    def dl_card(col, icon, title, desc, btn_label, data, mime, fname, color):
        with col:
            st.markdown(f"""
            <div style="background:{BG_SURFACE};border:1px solid {BG_BORDER};
                        border-top:2px solid {color};border-radius:8px;
                        padding:1.3rem;text-align:center;min-height:150px;">
              <div style="font-size:1.8rem;margin-bottom:0.5rem;">{icon}</div>
              <div style="font-family:{MONO};font-size:0.8rem;font-weight:700;
                          color:{TEXT_HI};margin-bottom:0.4rem;">{title}</div>
              <div style="font-size:0.74rem;color:{TEXT_MID};line-height:1.5;">{desc}</div>
            </div>""", unsafe_allow_html=True)
            st.download_button(f"⬇  {btn_label}", data=data, file_name=fname,
                               mime=mime, use_container_width=True)

    dl_card(c1,"📄","CSV Export","Raw data for Excel or pandas",
            "Download CSV", display_df.to_csv(index=False).encode(),
            "text/csv", f"flakydetect_{ts}.csv", CYAN)

    dl_card(c2,"📋","JSON Export","Structured for APIs and pipelines",
            "Download JSON", display_df.to_json(orient="records",indent=2).encode(),
            "application/json", f"flakydetect_{ts}.json", PURPLE)

    # Build rich markdown report
    md = [f"# FlakyDetect Report\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"]
    if st.session_state.exec_summary:
        md.append(f"## Executive Summary\n{st.session_state.exec_summary}\n")
    if "score" in df.columns:
        s = compute_stats(df)
        md.append(f"## Stats\n| Metric | Value |\n|---|---|\n"
                  f"| Total Tests | {s['total']} |\n| Critical | {s['critical']} |\n"
                  f"| Unstable | {s['unstable']} |\n| Stable | {s['stable']} |\n"
                  f"| Avg Score | {s['avg_score']:.1f} |\n")
    md.append(f"\n## Test Data\n{display_df.to_markdown(index=False)}\n")
    if st.session_state.ai_results:
        md.append("\n## AI Root-Cause Analysis\n")
        for tname, res in st.session_state.ai_results.items():
            md.append(f"### {tname}  (Tier: {res['tier'].upper()} · Fix: {res.get('difficulty','?')})\n"
                      f"**Analysis:** {res['explanation']}\n\n**Fixes:**\n")
            for sg in res["suggestions"]: md.append(f"- {sg}\n")
            if res.get("business_impact"):
                md.append(f"\n**Business Impact:** {res['business_impact']}\n")
            md.append("\n")

    dl_card(c3,"📝","Full Report","Markdown with AI analysis included",
            "Download .md", "\n".join(md).encode(),
            "text/markdown", f"flakydetect_report_{ts}.md", GREEN)

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("👁","Preview")
    tab1,tab2 = st.tabs(["📊  Data Table","🤖  AI Explanations"])
    with tab1:
        st.dataframe(display_df, use_container_width=True, height=300)
    with tab2:
        if st.session_state.ai_results:
            for tname, res in st.session_state.ai_results.items():
                with st.expander(f"{'🔴' if res['tier']=='high' else '🟡' if res['tier']=='med' else '🟢'}  {tname}"):
                    st.markdown(f"**{res['explanation']}**")
                    for s in res["suggestions"]: st.markdown(f"- {s}")
        else:
            callout("Run AI analysis to see explanations here.", "info")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5 — CHAT
# ═════════════════════════════════════════════════════════════════════════════

def page_chat():
    render_topbar("05 · Chat with Data")
    section_header("💬","Chat with Your Test Suite",
                   "Conversational AI powered by Groq · Llama 3.3 70B — asks follow-ups, remembers context")

    if st.session_state.df is None:
        empty_state("💬","No Data","Upload test data first.", "Go to Upload →")
        return

    df = st.session_state.df

    # ── Suggested prompts ──────────────────────────────────────────────────
    suggestions = [
        "Which tests should I fix first?",
        "Give me a prioritized fix plan",
        "What's causing the most failures?",
        "Which category has the most issues?",
        "Estimate total engineering time to fix all critical tests",
        "How would fixing critical tests improve our pass rate?",
    ]
    st.markdown(f"<div style='font-family:{MONO};font-size:0.62rem;color:{TEXT_LO};"
                f"letter-spacing:0.1em;margin-bottom:0.5rem;'>QUICK QUESTIONS</div>",
                unsafe_allow_html=True)
    r1,r2,r3 = st.columns(3)
    r4,r5,r6 = st.columns(3)
    for col, sug in zip([r1,r2,r3,r4,r5,r6], suggestions):
        if col.button(sug, use_container_width=True, key=f"s_{sug[:15]}"):
            st.session_state.chat_history.append({"role":"user","content":sug})
            with st.spinner("Groq is thinking…"):
                ans = ai_chat_answer(sug, df, st.session_state.chat_history)
            st.session_state.chat_history.append({"role":"assistant","content":ans})
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history ───────────────────────────────────────────────────────
    if not st.session_state.chat_history:
        empty_state("💬","Start Chatting",
                    "Click a question above or type your own below.",
                    "The AI knows your full test dataset")
    else:
        for msg in st.session_state.chat_history:
            chat_bubble(msg["role"], msg["content"])

    # ── Input row ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    ic,bc,cc = st.columns([5,1,1])
    with ic:
        user_input = st.text_input("","", placeholder="Ask anything about your test suite…",
                                   label_visibility="collapsed", key="chat_in")
    with bc:
        send = st.button("Send ➤", use_container_width=True)
    with cc:
        if st.button("🗑 Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    if send and user_input.strip():
        st.session_state.chat_history.append({"role":"user","content":user_input})
        with st.spinner("Groq is thinking…"):
            ans = ai_chat_answer(user_input, df, st.session_state.chat_history)
        st.session_state.chat_history.append({"role":"assistant","content":ans})
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═════════════════════════════════════════════════════════════════════════════
{
    "home":     page_home,
    "upload":   page_upload,
    "table":    page_table,
    "ai":       page_ai,
    "download": page_download,
    "chat":     page_chat,
}.get(page, page_home)()
