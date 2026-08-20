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
import csv
import io
from scoring_engine import score_invoice, score_batch, get_separation_stats

# ---- Page config ----
st.set_page_config(
    page_title="Setu — Invoice Trust Score",
    page_icon="🔏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Design system ----
# Concept: an official ledger / letterhead — the visual language of a verified
# government document (IRN stamps, GST seals, passbook rules) rather than a
# generic startup dashboard. Ink navy + brass seal accent on warm paper.
# Display: Fraunces (certificate/letterhead serif). Body: IBM Plex Sans.
# Data/figures: IBM Plex Mono (ledger-style numerals — GSTINs, IRNs, scores).
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

    /* ---- HARD OVERRIDE: force readable dark text everywhere on the light
       paper background. Streamlit sometimes falls back to light-on-dark
       text depending on the browser/OS theme; these rules stop that. ---- */
    .stApp, .stApp p, .stApp span, .stApp li, .stApp label,
    .stApp div, .stMarkdown, .stMarkdown p, .stMarkdown li,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span,
    [data-testid="stCaptionContainer"], .stCaption,
    [data-testid="stSelectbox"] label, [data-testid="stFileUploader"] label,
    [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] *,
    [data-testid="stWidgetLabel"] p {
        color: var(--ink) !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: var(--ink) !important;
    }
    /* Muted secondary text (captions, helper text) stays legible too */
    small, .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab"] p { color: var(--ink) !important; }
    .stTabs [aria-selected="true"] p { color: var(--brass) !important; }
    /* Selectbox selected value + dropdown options */
    [data-baseweb="select"] * { color: var(--ink) !important; }
    [data-baseweb="popover"] * { color: var(--ink) !important; }
    [data-baseweb="popover"] { background: #FFFFFF !important; }
    /* Dataframe / table text */
    [data-testid="stDataFrame"] * { color: var(--ink) !important; }
    [data-testid="stDataFrame"] { background: #FFFFFF !important; }
    /* Metric widgets already targeted below, reinforced here */
    [data-testid="stMetric"] label, [data-testid="stMetric"] div { color: var(--ink) !important; }
    /* File uploader button text */
    [data-testid="stFileUploader"] button { color: var(--ink) !important; }
    /* Alert boxes (success/warning/error) keep readable dark text on their tint */
    [data-testid="stAlert"] p, [data-testid="stAlert"] div { color: var(--ink) !important; }

    /* The letterhead banner is dark navy — its own text must stay light.
       These selectors are deliberately made MORE specific than the global
       .stApp div/p/span rule above (which would otherwise win and force
       invisible navy-on-navy text here). */
    .stApp .setu-letterhead,
    .stApp .setu-letterhead * {
        color: var(--paper) !important;
    }
    .stApp .setu-name { color: var(--paper) !important; }
    .stApp .setu-seal { color: var(--brass-bright) !important; }
    .stApp .setu-refno { color: rgba(245,240,228,0.55) !important; }
    .stApp .setu-tagline { color: rgba(245,240,228,0.82) !important; }
    .stApp .setu-tagline b { color: var(--brass-bright) !important; }

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
    .setu-wordmark {
        display: flex;
        align-items: center;
        gap: 12px;
    }
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

    .main-header { display: none; }
    .sub-header { display: none; }

    h3 {
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        color: var(--ink) !important;
    }

    .metric-card {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 18px;
        border: 1px solid var(--line);
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.9rem;
        font-weight: 700;
        line-height: 1.2;
        color: var(--ink);
    }
    .metric-label {
        font-size: 0.75rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
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
    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
    }

    .band-high-risk {
        border-left: 4px solid var(--risk);
        padding-left: 12px;
        background: #FFFFFF;
        border-radius: 0 8px 8px 0;
        padding-top: 4px; padding-bottom: 4px;
    }
    .band-watch {
        border-left: 4px solid var(--watch);
        padding-left: 12px;
        background: #FFFFFF;
        border-radius: 0 8px 8px 0;
        padding-top: 4px; padding-bottom: 4px;
    }
    .band-high-trust {
        border-left: 4px solid var(--trust);
        padding-left: 12px;
        background: #FFFFFF;
        border-radius: 0 8px 8px 0;
        padding-top: 4px; padding-bottom: 4px;
    }

    .reason-positive, .stApp span.reason-positive { color: var(--trust) !important; font-family: 'IBM Plex Sans', sans-serif; }
    .reason-negative, .stApp span.reason-negative { color: var(--risk) !important; font-family: 'IBM Plex Sans', sans-serif; }
    .reason-neutral, .stApp span.reason-neutral { color: var(--muted) !important; font-family: 'IBM Plex Sans', sans-serif; }

    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.9rem;
        font-family: 'IBM Plex Mono', monospace;
    }
    .score-high { background: rgba(47,110,91,0.12); color: var(--trust); }
    .score-mid { background: rgba(184,134,46,0.14); color: var(--watch); }
    .score-low { background: rgba(166,67,46,0.12); color: var(--risk); }

    hr { border-color: var(--line) !important; }

    .stButton > button {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        border-radius: 6px;
    }
    /* Primary button: navy background NEEDS light text — the global dark-text
       rule above would otherwise force navy text onto this navy button,
       making it invisible. This must come after and win. */
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
    /* Secondary/default button: white background, dark text (already
       readable via the global rule, reinforced explicitly here) */
    .stButton > button:not([kind="primary"]) {
        background: #FFFFFF !important;
        border: 1px solid var(--line) !important;
    }
    .stButton > button:not([kind="primary"]) p,
    .stButton > button:not([kind="primary"]) div,
    .stButton > button:not([kind="primary"]) span {
        color: var(--ink) !important;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
    }

    .honest-note {
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-left: 3px solid var(--brass);
        border-radius: 6px;
        padding: 18px 20px;
        font-size: 0.85rem;
        color: var(--ink-2);
        margin-top: 2rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


# ---- Header: the letterhead ----
import datetime
_ref = datetime.datetime.now().strftime("REF SETU/%Y%m%d/DEMO")
st.markdown(f"""
<div class="setu-letterhead">
    <div class="setu-topline">
        <div class="setu-wordmark">
            <div class="setu-seal">S</div>
            <div class="setu-name">Setu</div>
        </div>
        <div class="setu-refno">{_ref}<br>Invoice Trust Score · v0.2</div>
    </div>
    <div class="setu-tagline">
        Predicts whether a manufacturing invoice will be repaid — using <b>GST e-invoice</b>,
        <b>e-way bill</b> (dispatch &amp; closure), <b>ITC acceptance</b>, and buyer payment history.
        No buyer cooperation required.
    </div>
</div>
""", unsafe_allow_html=True)



# ---- Data source selection ----
tab1, tab2 = st.tabs(["📊 Run Backtest on Sample Data", "📁 Upload Your Own Data"])

with tab1:
    st.markdown("**Retrospective backtest:** score 200 past auto-component invoices from the Pune-Chakan cluster. Each invoice has a known outcome (repaid or defaulted). The question: did low scores catch the real defaults?")
    use_sample = st.button("Run scoring on sample data", type="primary", key="sample_btn")

with tab2:
    st.markdown("**Upload your CSV** with columns: `invoice_id`, `buyer_name`, `invoice_value`, `buyer_past_on_time`, `buyer_past_total`, `buyer_avg_days_late`, `itc_claimed_by_buyer`, `eway_bill_present`, `buyer_turnover_trend`, and optionally `outcome` (Repaid/Defaulted) for backtest mode.")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], key="upload")


# ---- Load and process data ----
data = None

if use_sample:
    data = pd.read_csv("data/sample_invoices.csv")
    st.session_state["data_loaded"] = True
elif uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.session_state["data_loaded"] = True
elif st.session_state.get("data_loaded"):
    # Keep showing results after initial load
    try:
        data = pd.read_csv("data/sample_invoices.csv")
    except:
        pass

if data is not None:
    # Convert to list of dicts for scoring
    invoices = data.to_dict("records")
    
    # Score all invoices
    scored = score_batch(invoices)
    
    # Get separation stats
    has_outcomes = "outcome" in data.columns
    if has_outcomes:
        stats = get_separation_stats(scored)
    
    # ---- SECTION 1: Summary metrics ----
    st.markdown("---")
    st.markdown("### Portfolio Summary")
    
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
    
    # ---- SECTION 2: The separation proof (only if outcomes are available) ----
    if has_outcomes:
        st.markdown("---")
        st.markdown("### The Proof: Do Defaults Cluster in Low Scores?")
        st.markdown("If the model works, the red (default) rate should be high in the left band and near zero on the right.")
        
        band_col1, band_col2, band_col3 = st.columns(3)
        
        with band_col1:
            band_data = stats["bands"]["High Risk"]
            st.markdown('<div class="band-high-risk">', unsafe_allow_html=True)
            st.markdown(f"**🔴 High Risk (Score 0-49)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with band_col2:
            band_data = stats["bands"]["Watch"]
            st.markdown('<div class="band-watch">', unsafe_allow_html=True)
            st.markdown(f"**🟡 Watch (Score 50-69)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with band_col3:
            band_data = stats["bands"]["High Trust"]
            st.markdown('<div class="band-high-trust">', unsafe_allow_html=True)
            st.markdown(f"**🟢 High Trust (Score 70-100)**")
            st.markdown(f"**{band_data['total']}** invoices")
            st.markdown(f"**{band_data['default_rate']}%** defaulted")
            st.markdown(f"Avg score: {band_data['avg_score']}")
            st.progress(min(band_data['default_rate'] / 100, 1.0))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Verdict
        if stats["catch_rate"] >= 60:
            st.success(f"**Signal confirmed:** {stats['catch_rate']}% of defaults landed in the High Risk band. The High Trust band had a {stats['bands']['High Trust']['default_rate']}% default rate. This score separates repaid from defaulted invoices — the same test, run on your actual loan book, would prove whether this works on real data.")
        elif stats["catch_rate"] >= 40:
            st.warning(f"**Partial signal:** {stats['catch_rate']}% of defaults caught. The separation exists but is moderate. Worth testing on real data to see if it strengthens.")
        else:
            st.error(f"**Weak signal:** Only {stats['catch_rate']}% of defaults caught. The score does not separate well on this data.")
    
    # ---- SECTION 3: Score distribution chart ----
    st.markdown("---")
    st.markdown("### Score Distribution")
    
    score_df = pd.DataFrame([{
        "Score": r["score"],
        "Band": r["band"],
        "Outcome": r["invoice"].get("outcome", "Unknown"),
    } for r in scored])
    
    # Histogram — score distribution across bands
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71-80", "81-90", "91-100"]
    score_df["Range"] = pd.cut(score_df["Score"], bins=bins, labels=labels)
    chart_data = score_df.groupby("Range", observed=True).size().reset_index(name="Invoices")
    chart_data["Range"] = chart_data["Range"].astype(str)
    st.bar_chart(chart_data.set_index("Range"))
    
    # ---- SECTION 4: Every invoice, scored ----
    st.markdown("---")
    st.markdown("### Every Invoice, Scored")
    st.markdown("Click any row to see the full reasoning.")
    
    # Build display dataframe
    display_data = []
    for r in sorted(scored, key=lambda x: x["score"]):
        inv = r["invoice"]
        
        # Color-coded score
        if r["score"] >= 70:
            score_display = f"🟢 {r['score']}"
        elif r["score"] >= 50:
            score_display = f"🟡 {r['score']}"
        else:
            score_display = f"🔴 {r['score']}"
        
        # Top reason
        top_reason = r["reasons"][0]["text"] if r["reasons"] else ""
        
        row = {
            "Invoice": inv.get("invoice_id", ""),
            "Buyer": inv.get("buyer_name", ""),
            "Value (₹)": f"₹{int(float(inv.get('total_invoice_value', inv.get('invoice_value', 0)))):,}",
            "Score": score_display,
            "Band": r["band"],
            "Top Signal": top_reason,
        }
        
        if has_outcomes:
            outcome = inv.get("outcome", "")
            row["Outcome"] = f"✓ {outcome}" if outcome == "Repaid" else f"✕ {outcome}"
        
        display_data.append(row)
    
    st.dataframe(
        pd.DataFrame(display_data),
        use_container_width=True,
        height=500,
    )
    
    # ---- SECTION 5: Deep dive on a single invoice ----
    st.markdown("---")
    st.markdown("### Invoice Deep Dive")
    
    invoice_ids = [r["invoice"].get("invoice_id", f"Invoice {i}") for i, r in enumerate(scored)]
    selected_id = st.selectbox("Select an invoice to see full reasoning:", invoice_ids)
    
    if selected_id:
        selected = next(r for r in scored if r["invoice"].get("invoice_id") == selected_id)
        inv = selected["invoice"]
        
        col_a, col_b = st.columns([1, 2])
        
        with col_a:
            st.markdown(f"**Invoice:** {inv.get('invoice_id', '')}")
            st.markdown(f"**Supplier:** {inv.get('supplier_name', '')}")
            st.markdown(f"**Buyer:** {inv.get('buyer_name', '')}")
            st.markdown(f"**Value:** ₹{int(float(inv.get('total_invoice_value', inv.get('invoice_value', 0)))):,}")
            st.markdown(f"**Date:** {inv.get('invoice_date', '')}")
            
            score_val = selected["score"]
            if score_val >= 70:
                st.markdown(f"### 🟢 Score: {score_val}/100")
            elif score_val >= 50:
                st.markdown(f"### 🟡 Score: {score_val}/100")
            else:
                st.markdown(f"### 🔴 Score: {score_val}/100")
            
            st.markdown(f"**Band:** {selected['band']}")
            
            if has_outcomes:
                outcome = inv.get("outcome", "")
                if outcome == "Repaid":
                    st.markdown(f"**Actual outcome:** ✓ Repaid")
                else:
                    st.markdown(f"**Actual outcome:** ✕ Defaulted")
        
        with col_b:
            st.markdown("**Why this score:**")
            for reason in selected["reasons"]:
                if reason["type"] == "positive":
                    st.markdown(f'<span class="reason-positive">✓ {reason["text"]}</span>', unsafe_allow_html=True)
                elif reason["type"] == "negative":
                    st.markdown(f'<span class="reason-negative">✕ {reason["text"]}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="reason-neutral">~ {reason["text"]}</span>', unsafe_allow_html=True)
            
            st.markdown(f"\n**Recommendation:** {selected['recommendation']}")
    
    # ---- SECTION 6: Buyer-level aggregation ----
    st.markdown("---")
    st.markdown("### Buyer Risk Map")
    st.markdown("Which buyers are your riskiest? Aggregated across all their invoices.")
    
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
    
    # ---- Honest note ----
    st.markdown("""
    <div class="honest-note">
        <strong>Honest note:</strong> This demo runs on illustrative sample data to show the scoring machinery works. 
        It does <strong>not</strong> prove the signal is real on actual lending data — only a retrospective backtest 
        on a real NBFC's closed loan book can prove that. That test is the ask: give us 200 of your closed MSME 
        invoices, we'll score them blind, and we'll see together if the signal holds.
        <br><br>
        Built by a Physics student at IIT Bombay, researching this problem full-time.
    </div>
    """, unsafe_allow_html=True)

else:
    # Landing state
    st.markdown("---")
    st.markdown("### How It Works")
    
    st.markdown("""
    **The problem:** NBFCs want to lend to Tier-2/3 manufacturing suppliers but can't tell which invoices are safe to fund.
    
    **What Setu does:** reads five signals from the supplier's own consented data — the buyer's payment history, ITC claim status, 
    e-way bill dispatch proof, payment speed, and turnover trend — and produces a score per invoice predicting whether the buyer will pay.
    
    **What's different:** existing platforms score the *company*. Setu scores each *invoice separately* — because the same supplier 
    might have a safe invoice to a reliable buyer and a risky invoice to a shaky buyer.
    
    **No buyer cooperation needed.** Every signal comes from the supplier's own GST data and Account Aggregator consent.
    
    👈 **Click "Run scoring on sample data" above** to see it work on 200 real-shaped auto-component invoices from the Pune-Chakan cluster.
    """)
