"""
Setu — Invoice Trust Score Platform
====================================
A Streamlit dashboard that:
1. Lets an NBFC upload invoices (CSV)
2. Scores each invoice 0-100
3. Shows separation (do defaults cluster in low scores?)
4. Shows per-invoice reasons
5. Shows portfolio summary

This is the demo you open on your laptop in front of an NBFC risk officer.
"""

import streamlit as st
import pandas as pd
import datetime
from scoring_engine import score_invoice, score_batch, get_separation_stats

# ---- Page config ----
st.set_page_config(
    page_title="Setu — Invoice Trust Score",
    page_icon="🔏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Design system ----
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

    :root {
        --ink: #17233D;
        --ink-2: #223151;
        --paper: #F5F0E4;
        --paper-2: #EDE6D4;
        --brass: #B8763E;
        --brass-bright: #D08F4E;
        --trust: #2F6E5B;
        --risk: #A6432E;
        --watch: #B8862E;
        --line: #D8CEB4;
        --muted: #6B6252;
    }

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .block-container { max-width: 1120px; padding-top: 1.2rem; }
    .stApp { background: var(--paper) !important; }

    .stApp, .stApp p, .stApp span, .stApp li, .stApp label,
    .stApp div, .stMarkdown, .stMarkdown p, .stMarkdown li,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span,
    [data-testid="stCaptionContainer"], .stCaption,
    [data-testid="stSelectbox"] label,
    [data-testid="stWidgetLabel"] p {
        color: var(--ink) !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: var(--ink) !important;
    }
    small, .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] p { color: var(--ink) !important; }
    .stTabs [aria-selected="true"] p { color: var(--brass) !important; }
    .stTabs, [data-baseweb="tab-list"], [data-baseweb="tab-panel"] {
        background: var(--paper) !important;
    }
    [data-baseweb="tab-list"] button { background: transparent !important; }

    /* ---- Invoice search dropdown (selectbox): this element's own
       background has stubbornly stayed dark no matter how much we tried
       to force it light. Instead of fighting that further, we make it a
       deliberate dark navy field with bright white text — same treatment
       as the letterhead — so it's guaranteed readable either way. ---- */
    [data-baseweb="select"] {
        background: var(--ink) !important;
        border-radius: 6px !important;
    }
    [data-baseweb="select"] * {
        color: #FFFFFF !important;
    }
    [data-baseweb="select"] svg {
        fill: #FFFFFF !important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"] {
        background: var(--ink) !important;
    }
    [data-baseweb="popover"] *, [data-baseweb="menu"] *,
    [role="listbox"] *, [role="option"] * {
        color: #FFFFFF !important;
    }
    [role="option"] {
        background: var(--ink) !important;
    }
    [role="option"]:hover, li[role="option"]:hover {
        background: var(--ink-2) !important;
    }

    /* ---- File uploader: same treatment — deliberate dark zone with
       guaranteed bright white text and icon, not fighting the background
       any further. ---- */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--ink) !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploaderDropzone"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stFileUploaderDropzone"] svg {
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }
    [data-testid="stFileUploader"] button {
        color: #FFFFFF !important;
        background: var(--ink-2) !important;
        border: 1px solid var(--brass) !important;
    }
    [data-testid="stFileUploader"] button * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    [data-testid="stDataFrame"] * { color: var(--ink) !important; }
    [data-testid="stDataFrame"] { background: #FFFFFF !important; }
    [data-testid="stMetric"] label, [data-testid="stMetric"] div { color: var(--ink) !important; }
    [data-testid="stAlert"] p, [data-testid="stAlert"] div { color: var(--ink) !important; }

    .stApp * { color: var(--ink); }

    /* Re-assert the letterhead's light text after the blanket rule above */
    .stApp .setu-letterhead, .stApp .setu-letterhead * { color: var(--paper) !important; }
    .stApp .setu-name { color: var(--paper) !important; }
    .stApp .setu-seal { color: var(--brass-bright) !important; }
    .stApp .setu-refno { color: rgba(245,240,228,0.55) !important; }
    .stApp .setu-tagline { color: rgba(245,240,228,0.82) !important; }
    .stApp .setu-tagline b { color: var(--brass-bright) !important; }
    .stApp button[kind="primary"] * { color: var(--paper) !important; }
    .stApp span.reason-positive { color: var(--trust) !important; }
    .stApp span.reason-negative { color: var(--risk) !important; }
    .stApp span.reason-neutral { color: var(--muted) !important; }

    /* Re-assert white text on the dark dropdown/uploader AFTER the blanket
       rule above, so those specific fixes still win */
    .stApp [data-baseweb="select"] *,
    .stApp [data-baseweb="popover"] *,
    .stApp [data-baseweb="menu"] *,
    .stApp [role="option"] *,
    .stApp [data-testid="stFileUploaderDropzone"] *,
    .stApp [data-testid="stFileUploader"] button * {
        color: #FFFFFF !important;
    }

    [data-testid="stExpander"] *, [data-testid="stRadio"] *,
    [data-testid="stCheckbox"] *, [data-testid="stSlider"] *,
    [data-testid="stTooltipIcon"] *, [data-testid="stToast"] *,
    [role="tooltip"] *, [role="dialog"] * {
        color: var(--ink) !important;
    }
    [data-testid="stExpander"], [role="dialog"], [role="tooltip"] {
        background: #FFFFFF !important;
    }

    html, body {
        background: var(--paper) !important;
        color-scheme: light !important;
    }
    .main, .block-container, [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"], [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"], [data-testid="stElementContainer"],
    section[data-testid="stSidebar"] {
        background: var(--paper) !important;
    }

    /* ---- Letterhead banner ---- */
    .setu-letterhead {
        background: var(--ink);
        background-image: linear-gradient(135deg, var(--ink) 0%, var(--ink-2) 100%);
        border-radius: 10px;
        padding: 28px 32px 24px;
        margin-bottom: 6px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(184,118,62,0.35);
    }
    .setu-letterhead::after {
        content: "";
        position: absolute;
        top: 0; right: 0; bottom: 0;
        width: 6px;
        background: repeating-linear-gradient(
            180deg, var(--brass) 0px, var(--brass) 10px, transparent 10px, transparent 20px
        );
        opacity: 0.6;
    }
    .setu-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }
    .setu-wordmark { display: flex; align-items: center; gap: 12px; }
    .setu-seal {
        width: 40px; height: 40px;
        border-radius: 50%;
        border: 2px solid var(--brass);
        display: flex; align-items: center; justify-content: center;
        font-family: 'Fraunces', serif;
        font-weight: 700;
        font-size: 17px;
        color: var(--brass-bright);
        flex-shrink: 0;
        background: rgba(184,118,62,0.08);
    }
    .setu-name {
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.9rem;
        color: var(--paper);
        letter-spacing: 0.01em;
        line-height: 1;
    }
    .setu-refno {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: rgba(245,240,228,0.55);
        letter-spacing: 0.06em;
        text-align: right;
    }
    .setu-tagline {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.98rem;
        color: rgba(245,240,228,0.82);
        max-width: 62ch;
        line-height: 1.5;
        border-top: 1px solid rgba(184,118,62,0.3);
        padding-top: 14px;
    }
    .setu-tagline b { color: var(--brass-bright); font-weight: 600; }

    h3 {
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        color: var(--ink) !important;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace !important;
        color: var(--ink) !important;
    }
    [data-testid="stMetricLabel"] { color: var(--muted) !important; }

    .band-high-risk {
        border-left: 4px solid var(--risk);
        padding-left: 12px; background: #FFFFFF;
        border-radius: 0 8px 8px 0; padding-top: 4px; padding-bottom: 4px;
    }
    .band-watch {
        border-left: 4px solid var(--watch);
        padding-left: 12px; background: #FFFFFF;
        border-radius: 0 8px 8px 0; padding-top: 4px; padding-bottom: 4px;
    }
    .band-high-trust {
        border-left: 4px solid var(--trust);
        padding-left: 12px; background: #FFFFFF;
        border-radius: 0 8px 8px 0; padding-top: 4px; padding-bottom: 4px;
    }

    .reason-positive, .stApp span.reason-positive { color: var(--trust) !important; }
    .reason-negative, .stApp span.reason-negative { color: var(--risk) !important; }
    .reason-neutral, .stApp span.reason-neutral { color: var(--muted) !important; }

    hr { border-color: var(--line) !important; }

    .stButton > button {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        border-radius: 6px;
    }
    .stButton > button[kind="primary"] {
        background: var(--ink) !important;
        border: 1px solid var(--brass) !important;
    }
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] div,
    .stButton > button[kind="primary"] span {
        color: var(--paper) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--ink-2) !important;
        border-color: var(--brass-bright) !important;
    }
    .stButton > button:not([kind="primary"]) {
        background: #FFFFFF !important;
        border: 1px solid var(--line) !important;
    }
    .stButton > button:not([kind="primary"]) p,
    .stButton > button:not([kind="primary"]) div,
    .stButton > button:not([kind="primary"]) span {
        color: var(--ink) !important;
    }
</style>
""", unsafe_allow_html=True)


# ---- Header: the letterhead ----
_ref = datetime.datetime.now().strftime("REF SETU/%Y%m%d/DEMO")
st.markdown(f"""
<div class="setu-letterhead">
    <div class="setu-topline">
        <div class="setu-wordmark">
            <div class="setu-seal">S</div>
            <div class="setu-name">Setu</div>
        </div>
        <div class="setu-refno">{_ref}<br>Invoice Trust Score · v0.3</div>
    </div>
    <div class="setu-tagline">
        Predicts whether a manufacturing invoice will be repaid — using <b>GST e-invoice</b>,
        <b>e-way bill</b> (dispatch &amp; closure), <b>ITC acceptance</b>, and buyer payment history.
        No buyer cooperation required.
    </div>
</div>
""", unsafe_allow_html=True)


# ---- Data source selection — back to switchable tabs, minimal text ----
tab1, tab2 = st.tabs(["Run on sample data", "Upload your own data"])

with tab1:
    use_sample = st.button("Run scoring on sample data", type="primary", key="sample_btn")

with tab2:
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], key="upload")


# ---- Load and process data ----
data = None

if use_sample:
    data = pd.read_csv("sample_invoices.csv")
    st.session_state["data_loaded"] = True
elif uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.session_state["data_loaded"] = True
elif st.session_state.get("data_loaded"):
    try:
        data = pd.read_csv("sample_invoices.csv")
    except Exception:
        pass

if data is not None:
    invoices = data.to_dict("records")
    scored = score_batch(invoices)

    has_outcomes = "outcome" in data.columns
    if has_outcomes:
        stats = get_separation_stats(scored)

    # ---- SECTION 1: Summary metrics ----
    st.markdown("---")
    st.markdown("### Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Invoices Scored", len(scored))

    with col2:
        avg_score = round(sum(r["score"] for r in scored) / len(scored), 1)
        st.metric("Average Trust Score", f"{avg_score}/100")

    with col3:
        high_risk_count = sum(1 for r in scored if r["band"] == "High Risk")
        st.metric("High Risk Invoices", f"{high_risk_count} ({round(100*high_risk_count/len(scored))}%)")

    with col4:
        if has_outcomes:
            st.metric("Defaults Caught in Low Band", f"{stats['catch_rate']}%")
        else:
            high_trust_count = sum(1 for r in scored if r["band"] == "High Trust")
            st.metric("High Trust Invoices", f"{high_trust_count} ({round(100*high_trust_count/len(scored))}%)")

    # ---- SECTION 2: The separation proof ----
    if has_outcomes:
        st.markdown("---")
        st.markdown("### Summary")

        band_col1, band_col2, band_col3 = st.columns(3)

        with band_col1:
            band_data = stats["bands"]["High Risk"]
            st.markdown('<div class="band-high-risk">', unsafe_allow_html=True)
            st.markdown("**🔴 High Risk (Score 0-49)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)

        with band_col2:
            band_data = stats["bands"]["Watch"]
            st.markdown('<div class="band-watch">', unsafe_allow_html=True)
            st.markdown("**🟡 Watch (Score 50-69)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)

        with band_col3:
            band_data = stats["bands"]["High Trust"]
            st.markdown('<div class="band-high-trust">', unsafe_allow_html=True)
            st.markdown("**🟢 High Trust (Score 70-100)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)

        if stats["catch_rate"] >= 60:
            st.success(f"**Signal confirmed:** {stats['catch_rate']}% of defaults landed in the High Risk band. The High Trust band had a {stats['bands']['High Trust']['default_rate']}% default rate.")
        elif stats["catch_rate"] >= 40:
            st.warning(f"**Partial signal:** {stats['catch_rate']}% of defaults caught.")
        else:
            st.error(f"**Weak signal:** Only {stats['catch_rate']}% of defaults caught.")

    # ---- SECTION 3: Score distribution chart ----
    st.markdown("---")
    st.markdown("### Score distribution")

    score_df = pd.DataFrame([{
        "Score": r["score"],
        "Band": r["band"],
        "Outcome": r["invoice"].get("outcome", "Unknown"),
    } for r in scored])

    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71-80", "81-90", "91-100"]
    score_df["Score range"] = pd.cut(score_df["Score"], bins=bins, labels=labels)
    chart_data = score_df.groupby("Score range", observed=True).size().reset_index(name="Number of invoices")
    chart_data["Score range"] = chart_data["Score range"].astype(str)
    st.bar_chart(chart_data.set_index("Score range"), x_label="Score range", y_label="Number of invoices")

    # ---- SECTION 4: Every invoice, scored (custom table, not canvas grid) ----
    st.markdown("---")
    st.markdown("### All invoices")
    st.markdown("Click any row to see the full reasoning.")

    table_rows_html = ""
    for r in sorted(scored, key=lambda x: x["score"]):
        inv = r["invoice"]
        if r["score"] >= 70:
            score_color, score_emoji = "var(--trust)", "🟢"
        elif r["score"] >= 50:
            score_color, score_emoji = "var(--watch)", "🟡"
        else:
            score_color, score_emoji = "var(--risk)", "🔴"

        top_reason = r["reasons"][0]["text"] if r["reasons"] else ""
        value_str = f"₹{int(float(inv.get('total_invoice_value', inv.get('invoice_value', 0)))):,}"

        outcome_cell = ""
        if has_outcomes:
            outcome = inv.get("outcome", "")
            outcome_color = "var(--trust)" if outcome == "Repaid" else "var(--risk)"
            outcome_symbol = "✓" if outcome == "Repaid" else "✕"
            outcome_cell = f'<td style="padding:8px 10px; color:{outcome_color}; font-weight:600;">{outcome_symbol} {outcome}</td>'

        table_rows_html += f'''<tr style="border-top:1px solid var(--line);">
            <td style="padding:8px 10px; color:var(--ink); font-family:'IBM Plex Mono',monospace;">{inv.get("invoice_id","")}</td>
            <td style="padding:8px 10px; color:var(--ink);">{inv.get("buyer_name","")}</td>
            <td style="padding:8px 10px; color:var(--ink); font-family:'IBM Plex Mono',monospace;">{value_str}</td>
            <td style="padding:8px 10px; color:{score_color}; font-weight:700; font-family:'IBM Plex Mono',monospace;">{score_emoji} {r["score"]}</td>
            <td style="padding:8px 10px; color:{score_color}; font-weight:600;">{r["band"]}</td>
            <td style="padding:8px 10px; color:var(--muted); font-size:0.85rem;">{top_reason}</td>
            {outcome_cell}
        </tr>'''

    outcome_header = '<th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Outcome</th>' if has_outcomes else ""

    table_html = f'''
    <div style="max-height:500px; overflow-y:auto; border:1px solid var(--line); border-radius:8px;">
    <table style="width:100%; border-collapse:collapse; font-family:'IBM Plex Sans',sans-serif; font-size:0.9rem;">
        <thead style="position:sticky; top:0; z-index:1;">
            <tr style="background:var(--ink);">
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Invoice</th>
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Buyer</th>
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Value</th>
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Score</th>
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Band</th>
                <th style="padding:10px; text-align:left; color:#FFFFFF; font-weight:700;">Top signal</th>
                {outcome_header}
            </tr>
        </thead>
        <tbody style="background:#FFFFFF;">
            {table_rows_html}
        </tbody>
    </table>
    </div>
    '''
    st.markdown(table_html, unsafe_allow_html=True)

    # ---- SECTION 5: Deep dive on a single invoice — searchable selectbox restored ----
    st.markdown("---")
    st.markdown("### Each invoice")

    invoice_ids = [r["invoice"].get("invoice_id", f"Invoice {i}") for i, r in enumerate(scored)]
    selected_id = st.selectbox("Search for an invoice:", invoice_ids)

    if selected_id:
        selected = next(r for r in scored if r["invoice"].get("invoice_id") == selected_id)
        inv = selected["invoice"]

        score_val = selected["score"]
        if score_val >= 70:
            score_color, score_emoji = "var(--trust)", "🟢"
        elif score_val >= 50:
            score_color, score_emoji = "var(--watch)", "🟡"
        else:
            score_color, score_emoji = "var(--risk)", "🔴"

        outcome_line = ""
        if has_outcomes:
            outcome = inv.get("outcome", "")
            outcome_color = "var(--trust)" if outcome == "Repaid" else "var(--risk)"
            outcome_symbol = "✓" if outcome == "Repaid" else "✕"
            outcome_line = f'<div style="margin-top:6px; color:{outcome_color}; font-weight:600;">{outcome_symbol} {outcome}</div>'

        reasons_html = ""
        for reason in selected["reasons"]:
            if reason["type"] == "positive":
                r_color, r_symbol = "var(--trust)", "✓"
            elif reason["type"] == "negative":
                r_color, r_symbol = "var(--risk)", "✕"
            else:
                r_color, r_symbol = "var(--muted)", "~"
            reasons_html += f'<div style="padding:6px 0; color:{r_color}; font-size:0.95rem;">{r_symbol} {reason["text"]}</div>'

        value_str = f"₹{int(float(inv.get('total_invoice_value', inv.get('invoice_value', 0)))):,}"

        card_html = f'''
        <div style="background:#FFFFFF; border:1px solid var(--line); border-radius:12px; padding:20px 24px; margin-top:8px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
                <div>
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.95rem; color:var(--ink); font-weight:600;">{inv.get("invoice_id","")}</div>
                    <div style="color:var(--muted); font-size:0.85rem; margin-top:4px;">{inv.get("supplier_name","")} → {inv.get("buyer_name","")}</div>
                    <div style="color:var(--ink); font-size:0.9rem; margin-top:4px;">{value_str} · {inv.get("invoice_date","")}</div>
                    {outcome_line}
                </div>
                <div style="text-align:right;">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:2rem; font-weight:700; color:{score_color};">{score_emoji} {score_val}</div>
                    <div style="color:{score_color}; font-weight:600; font-size:0.9rem;">{selected["band"]}</div>
                </div>
            </div>
            <div style="border-top:1px solid var(--line); margin-top:16px; padding-top:12px;">
                <div style="color:var(--ink); font-weight:600; margin-bottom:6px;">Why this score</div>
                {reasons_html}
            </div>
            <div style="border-top:1px solid var(--line); margin-top:12px; padding-top:12px; color:var(--ink);">
                <b>Recommendation:</b> {selected["recommendation"]}
            </div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)

    # ---- SECTION 6: Buyer-level aggregation ----
    st.markdown("---")
    st.markdown("### Most risky buyers")

    buyer_stats = {}
    for r in scored:
        buyer = r["invoice"].get("buyer_name", "Unknown")
        if buyer not in buyer_stats:
            buyer_stats[buyer] = {"scores": [], "defaults": 0, "total": 0, "total_value": 0}
        buyer_stats[buyer]["scores"].append(r["score"])
        buyer_stats[buyer]["total"] += 1
        buyer_stats[buyer]["total_value"] += float(r["invoice"].get("total_invoice_value", r["invoice"].get("invoice_value", 0)))
        if r["invoice"].get("outcome", "").lower() in ("defaulted", "default"):
            buyer_stats[buyer]["defaults"] += 1

    buyer_display = []
    for buyer, bdata in sorted(buyer_stats.items(), key=lambda x: sum(x[1]["scores"])/len(x[1]["scores"])):
        avg = round(sum(bdata["scores"]) / len(bdata["scores"]), 1)
        def_rate = round(100 * bdata["defaults"] / bdata["total"], 1) if bdata["total"] > 0 else 0

        if avg >= 70:
            risk_indicator = "🟢 Low Risk"
        elif avg >= 50:
            risk_indicator = "🟡 Watch"
        else:
            risk_indicator = "🔴 High Risk"

        buyer_display.append({
            "Buyer": buyer,
            "Avg Score": avg,
            "Risk Level": risk_indicator,
            "Invoices": bdata["total"],
            "Total Exposure (₹)": f"₹{int(bdata['total_value']):,}",
            "Default Rate": f"{def_rate}%",
        })

    st.dataframe(pd.DataFrame(buyer_display), use_container_width=True)

else:
    st.markdown("---")
    st.markdown("### How it works")

    st.markdown("""
    **The problem:** NBFCs want to lend to Tier-2/3 manufacturing suppliers but can't tell which invoices are safe to fund.

    **What Setu does:** reads signals from the supplier's own consented data — the buyer's payment history, ITC claim status,
    e-way bill dispatch and closure, and GST filing pattern — and produces a score per invoice predicting whether the buyer will pay.

    **No buyer cooperation needed.** Every signal comes from the supplier's own GST data and Account Aggregator consent.

    👈 Click a tab above to get started.
    """)
