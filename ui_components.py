"""
ui_components.py  —  FlakyDetect Professional Edition
Clean, minimal design. One accent color. No noise.
"""
import streamlit as st

# ── Design Tokens ─────────────────────────────────────────────────────────────
# Monochrome base + single blue accent + semantic red/green only where needed
BG_BASE    = "#0C0C0E"   # near-black
BG_SURFACE = "#111115"   # card background
BG_RAISED  = "#18181D"   # elevated surface
BG_BORDER  = "#222228"   # borders
ACCENT     = "#4F6EF7"   # single blue accent — used sparingly
RED        = "#E5484D"   # errors / critical only
AMBER      = "#F5A623"   # warnings only
GREEN      = "#3DD68C"   # success only
TEXT_HI    = "#EDEDEF"   # primary text
TEXT_MID   = "#8B8B99"   # secondary text
TEXT_LO    = "#4A4A56"   # muted / labels
MONO       = "'JetBrains Mono', 'Fira Code', monospace"
SANS       = "'Inter', system-ui, sans-serif"


def inject_global_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; }}

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {{
        background: {BG_BASE} !important;
        color: {TEXT_HI};
        font-family: {SANS};
        font-size: 14px;
    }}

    [data-testid="stHeader"],
    [data-testid="stDecoration"],
    #MainMenu, footer, .stDeployButton {{ display: none !important; }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: {BG_SURFACE} !important;
        border-right: 1px solid {BG_BORDER} !important;
    }}
    [data-testid="stSidebar"] * {{ color: {TEXT_HI} !important; }}
    [data-testid="stSidebarContent"] {{ padding: 0 !important; }}

    /* ── Radio nav ── */
    [data-testid="stSidebar"] .stRadio > div {{ gap: 1px !important; }}
    [data-testid="stSidebar"] .stRadio label {{
        padding: 0.5rem 1rem !important;
        border-radius: 4px !important;
        font-size: 0.84rem !important;
        color: {TEXT_MID} !important;
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: {BG_RAISED} !important;
        color: {TEXT_HI} !important;
    }}

    /* ── Buttons ── */
    .stButton > button {{
        background: {ACCENT} !important;
        color: #fff !important;
        font-family: {SANS} !important;
        font-weight: 500 !important;
        font-size: 0.84rem !important;
        border: none !important;
        border-radius: 5px !important;
        padding: 0.5rem 1.2rem !important;
        transition: opacity 0.15s, transform 0.15s !important;
        letter-spacing: 0 !important;
        text-transform: none !important;
    }}
    .stButton > button:hover {{
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px {ACCENT}33 !important;
    }}

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: {BG_RAISED} !important;
        color: {TEXT_HI} !important;
        border: 1px solid {BG_BORDER} !important;
        border-radius: 5px !important;
        font-family: {SANS} !important;
        font-size: 0.86rem !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 2px {ACCENT}1A !important;
        outline: none !important;
    }}
    .stSelectbox > div > div {{
        background: {BG_RAISED} !important;
        border: 1px solid {BG_BORDER} !important;
        border-radius: 5px !important;
        color: {TEXT_HI} !important;
        font-size: 0.86rem !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: transparent;
        border-bottom: 1px solid {BG_BORDER};
        padding: 0;
        gap: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {TEXT_MID} !important;
        font-family: {SANS} !important;
        font-size: 0.84rem !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        background: transparent !important;
        transition: color 0.15s;
    }}
    .stTabs [aria-selected="true"] {{
        color: {TEXT_HI} !important;
        border-bottom-color: {ACCENT} !important;
        background: transparent !important;
    }}

    /* ── Progress ── */
    .stProgress > div > div > div > div {{
        background: {ACCENT} !important;
    }}

    /* ── Expander ── */
    .streamlit-expanderHeader {{
        background: {BG_SURFACE} !important;
        border: 1px solid {BG_BORDER} !important;
        border-radius: 5px !important;
        font-size: 0.84rem !important;
        color: {TEXT_HI} !important;
        padding: 0.65rem 1rem !important;
    }}
    .streamlit-expanderContent {{
        background: {BG_SURFACE} !important;
        border: 1px solid {BG_BORDER} !important;
        border-top: none !important;
        border-radius: 0 0 5px 5px !important;
        padding: 1rem !important;
    }}

    /* ── Dataframe ── */
    .stDataFrame {{
        border: 1px solid {BG_BORDER} !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }}

    /* ── File uploader ── */
    [data-testid="stFileUploader"] > div {{
        background: {BG_SURFACE} !important;
        border: 1px dashed {BG_BORDER} !important;
        border-radius: 6px !important;
        transition: border-color 0.2s;
    }}
    [data-testid="stFileUploader"] > div:hover {{
        border-color: {ACCENT}66 !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {BG_BORDER}; border-radius: 2px; }}

    /* ── Checkbox ── */
    .stCheckbox > label {{ font-size: 0.84rem !important; color: {TEXT_MID} !important; }}

    /* ── Fade in ── */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .fade {{ animation: fadeIn 0.3s ease both; }}

    /* ── Status dot pulse ── */
    @keyframes pulse {{
        0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ── Top bar ───────────────────────────────────────────────────────────────────
def render_topbar(page_title=""):
    st.markdown(f"""
    <div style="
        display:flex; align-items:center; justify-content:space-between;
        padding:0.75rem 1.5rem;
        border-bottom:1px solid {BG_BORDER};
        margin-bottom:1.8rem;
        background:{BG_SURFACE};">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-family:{MONO};font-size:0.78rem;font-weight:500;
                     color:{TEXT_HI};letter-spacing:0.02em;">FlakyDetect</span>
        <span style="color:{BG_BORDER};">·</span>
        <span style="font-size:0.78rem;color:{TEXT_MID};">{page_title}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div style="width:6px;height:6px;border-radius:50%;background:{GREEN};
                    animation:pulse 2.5s infinite;"></div>
        <span style="font-size:0.74rem;color:{TEXT_MID};">Groq · Llama 3.3 70B</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar(has_data=False, is_analyzed=False):
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:1.2rem 1rem 1rem;">
          <div style="font-family:{MONO};font-size:0.82rem;font-weight:500;
                      color:{TEXT_HI};">FlakyDetect</div>
          <div style="font-size:0.72rem;color:{TEXT_LO};margin-top:2px;">
            Test Reliability Platform
          </div>
        </div>
        <div style="height:1px;background:{BG_BORDER};margin:0 0 0.5rem;"></div>
        """, unsafe_allow_html=True)

        pages = {
            "Overview":          "home",
            "Upload Data":       "upload",
            "Flaky Test Table":  "table",
            "AI Explanation":    "ai",
            "Download Report":   "download",
            "Chat with Data":    "chat",
        }
        sel = st.radio("", list(pages.keys()), label_visibility="collapsed")

        st.markdown(f"""
        <div style="height:1px;background:{BG_BORDER};margin:0.8rem 0;"></div>
        <div style="padding:0.75rem 1rem;">
          <div style="font-size:0.7rem;color:{TEXT_LO};margin-bottom:0.6rem;
                      text-transform:uppercase;letter-spacing:0.08em;">Status</div>
          <div style="display:flex;flex-direction:column;gap:5px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:0.78rem;color:{TEXT_MID};">Data loaded</span>
              <span style="font-size:0.74rem;font-family:{MONO};
                           color:{'"+GREEN+"' if has_data else '"+TEXT_LO+"'};">
                {'yes' if has_data else 'no'}
              </span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:0.78rem;color:{TEXT_MID};">AI analyzed</span>
              <span style="font-size:0.74rem;font-family:{MONO};
                           color:{'"+GREEN+"' if is_analyzed else '"+TEXT_LO+"'};">
                {'yes' if is_analyzed else 'no'}
              </span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        return pages[sel]


# ── Section header ────────────────────────────────────────────────────────────
def section_header(icon, title, subtitle=""):
    sub_html = (f"<p style='margin:3px 0 0;font-size:0.78rem;color:{TEXT_MID};"
                f"line-height:1.4;'>{subtitle}</p>") if subtitle else ""
    st.markdown(f"""
    <div class="fade" style="margin-bottom:1.2rem;">
      <h2 style="font-size:0.96rem;font-weight:600;color:{TEXT_HI};
                 display:flex;align-items:center;gap:7px;margin:0;">
        <span style="font-size:1rem;">{icon}</span>{title}
      </h2>
      {sub_html}
      <div style="height:1px;background:{BG_BORDER};margin-top:10px;"></div>
    </div>
    """, unsafe_allow_html=True)


# ── KPI row ───────────────────────────────────────────────────────────────────
def kpi_row(metrics: list):
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        color = m.get("color", TEXT_HI)
        sub   = m.get("sub", "")
        col.markdown(f"""
        <div class="fade" style="
            background:{BG_SURFACE};
            border:1px solid {BG_BORDER};
            border-radius:6px;
            padding:1rem 1.1rem;">
          <div style="font-size:0.7rem;color:{TEXT_LO};text-transform:uppercase;
                      letter-spacing:0.07em;margin-bottom:5px;">{m['label']}</div>
          <div style="font-size:1.5rem;font-weight:600;color:{color};
                      font-family:{MONO};line-height:1;">{m['value']}</div>
          {"<div style='font-size:0.72rem;color:"+TEXT_LO+";margin-top:4px;'>"+sub+"</div>" if sub else ""}
        </div>
        """, unsafe_allow_html=True)


# ── Score badge ───────────────────────────────────────────────────────────────
def score_badge_html(score: float) -> str:
    if score >= 75:
        color, label = RED, "critical"
    elif score >= 40:
        color, label = AMBER, "unstable"
    else:
        color, label = GREEN, "stable"
    w = int(score)
    return f"""
    <div style="display:flex;align-items:center;gap:8px;padding:5px 0;">
      <div style="width:80px;height:4px;background:{BG_BORDER};border-radius:2px;overflow:hidden;">
        <div style="width:{w}%;height:100%;background:{color};border-radius:2px;"></div>
      </div>
      <span style="font-family:{MONO};font-size:0.8rem;color:{TEXT_HI};min-width:24px;">{score:.0f}</span>
      <span style="font-size:0.7rem;color:{color};">{label}</span>
    </div>"""


# ── Run pattern dots ──────────────────────────────────────────────────────────
def pattern_html(pattern: list) -> str:
    dots = ""
    for p in pattern[-14:]:
        if str(p).upper() in ("PASS","1","TRUE","P","SUCCESS","PASSED"):
            dots += f"<span style='color:{GREEN};font-size:0.65rem;' title='PASS'>●</span>"
        else:
            dots += f"<span style='color:{RED};font-size:0.65rem;' title='FAIL'>●</span>"
    return f"<div style='display:flex;gap:3px;align-items:center;padding:5px 0;'>{dots}</div>"


# ── Callout ───────────────────────────────────────────────────────────────────
def callout(text: str, kind: str = "info"):
    cfg = {
        "info":    (ACCENT, "ℹ"),
        "success": (GREEN,  "✓"),
        "warn":    (AMBER,  "⚠"),
        "error":   (RED,    "✕"),
    }
    c, icon = cfg.get(kind, cfg["info"])
    st.markdown(f"""
    <div class="fade" style="
        background:{BG_SURFACE};
        border:1px solid {BG_BORDER};
        border-left:2px solid {c};
        border-radius:5px;
        padding:0.7rem 1rem;
        display:flex;gap:9px;align-items:flex-start;
        margin:0.4rem 0;">
      <span style="color:{c};font-size:0.82rem;margin-top:1px;flex-shrink:0;">{icon}</span>
      <span style="font-size:0.82rem;color:{TEXT_HI};line-height:1.55;">{text}</span>
    </div>
    """, unsafe_allow_html=True)


# ── AI result card ────────────────────────────────────────────────────────────
def ai_card(test_name, explanation, suggestions, confidence, tier, difficulty="Medium"):
    tier_color = RED if tier=="high" else AMBER if tier=="med" else GREEN
    tier_label = "Critical" if tier=="high" else "Unstable" if tier=="med" else "Stable"
    sugg_items = "".join(
        f"<li style='margin-bottom:6px;color:{TEXT_HI};'>{s}</li>"
        for s in suggestions
    )
    st.markdown(f"""
    <div class="fade" style="
        background:{BG_SURFACE};
        border:1px solid {BG_BORDER};
        border-radius:6px;
        padding:1.3rem;
        margin-bottom:1rem;">

      <div style="display:flex;align-items:flex-start;justify-content:space-between;
                  margin-bottom:1rem;flex-wrap:wrap;gap:8px;">
        <div>
          <div style="font-size:0.88rem;font-weight:600;color:{TEXT_HI};">{test_name}</div>
          <div style="font-size:0.74rem;color:{TEXT_MID};margin-top:2px;">
            Groq · Llama 3.3 70B
          </div>
        </div>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <span style="font-size:0.72rem;color:{tier_color};background:{BG_RAISED};
                       border:1px solid {BG_BORDER};border-radius:4px;padding:2px 8px;">
            {tier_label}
          </span>
          <span style="font-size:0.72rem;color:{TEXT_MID};background:{BG_RAISED};
                       border:1px solid {BG_BORDER};border-radius:4px;padding:2px 8px;">
            {confidence}% confidence
          </span>
          <span style="font-size:0.72rem;color:{TEXT_MID};background:{BG_RAISED};
                       border:1px solid {BG_BORDER};border-radius:4px;padding:2px 8px;">
            Fix: {difficulty}
          </span>
        </div>
      </div>

      <div style="background:{BG_RAISED};border-radius:5px;padding:0.9rem 1rem;margin-bottom:0.8rem;">
        <div style="font-size:0.7rem;color:{TEXT_LO};text-transform:uppercase;
                    letter-spacing:0.07em;margin-bottom:6px;">Root cause</div>
        <p style="font-size:0.84rem;color:{TEXT_HI};line-height:1.65;margin:0;">{explanation}</p>
      </div>

      <div style="background:{BG_RAISED};border-radius:5px;padding:0.9rem 1rem;">
        <div style="font-size:0.7rem;color:{TEXT_LO};text-transform:uppercase;
                    letter-spacing:0.07em;margin-bottom:8px;">Recommended fixes</div>
        <ul style="margin:0;padding-left:1.1rem;font-size:0.82rem;line-height:1.7;">
          {sugg_items}
        </ul>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Chat bubble ───────────────────────────────────────────────────────────────
def chat_bubble(role: str, content: str):
    is_user = role == "user"
    bg      = BG_RAISED if is_user else BG_SURFACE
    border  = f"1px solid {ACCENT}33" if is_user else f"1px solid {BG_BORDER}"
    align   = "flex-end" if is_user else "flex-start"
    avatar  = "You" if is_user else "AI"
    av_color= TEXT_MID if is_user else ACCENT
    direction = "row-reverse" if is_user else "row"
    st.markdown(f"""
    <div style="display:flex;justify-content:{align};margin-bottom:0.8rem;">
      <div style="display:flex;flex-direction:{direction};align-items:flex-start;
                  gap:8px;max-width:78%;">
        <div style="font-size:0.68rem;color:{av_color};font-family:{MONO};
                    padding-top:3px;flex-shrink:0;font-weight:500;">{avatar}</div>
        <div style="background:{bg};border:{border};border-radius:6px;
                    padding:0.7rem 0.9rem;font-size:0.83rem;color:{TEXT_HI};
                    line-height:1.6;">{content}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Empty state ───────────────────────────────────────────────────────────────
def empty_state(icon, title, body, action=""):
    st.markdown(f"""
    <div class="fade" style="
        text-align:center;padding:3rem 2rem;
        background:{BG_SURFACE};
        border:1px solid {BG_BORDER};
        border-radius:6px;margin:1rem 0;">
      <div style="font-size:1.8rem;margin-bottom:0.7rem;">{icon}</div>
      <div style="font-size:0.9rem;font-weight:600;color:{TEXT_HI};margin-bottom:0.4rem;">{title}</div>
      <div style="font-size:0.8rem;color:{TEXT_MID};max-width:300px;
                  margin:0 auto;line-height:1.5;">{body}</div>
      {"<div style='font-size:0.78rem;color:"+ACCENT+";margin-top:0.7rem;'>→ "+action+"</div>" if action else ""}
    </div>
    """, unsafe_allow_html=True)

