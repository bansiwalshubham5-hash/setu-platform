"""
Setu Invoice Trust Scoring Engine — Version 2
===============================================
Updated with real government document field names and the NEW
e-way bill closure signal (GSTN Advisory 664, effective Aug 1 2026).

Seven signals now (was five):
1. Buyer payment history (highest weight — direct evidence)
2. Buyer ITC claim status (acceptance proxy from GSTR-2B)
3. Buyer average days late (severity of delay pattern)
4. E-way bill present (dispatch proof from EWB-01)
5. E-way bill CLOSED (NEW — delivery confirmation, Aug 1 2026)
6. E-invoice IRN valid (fraud check from Form GST INV-01)
7. Buyer GSTR-3B filing pattern (NEW — financial health leading indicator)
"""


def score_invoice(invoice: dict) -> dict:
    score = 50
    reasons = []
    
    # --- SIGNAL 1: Buyer payment history (±25 points) ---
    past_on_time = int(invoice.get("buyer_past_on_time", 0))
    past_total = int(invoice.get("buyer_past_total", 6))
    
    if past_total > 0:
        pay_rate = past_on_time / past_total
        if pay_rate >= 0.85:
            score += 25
            reasons.append({"type": "positive", "text": f"Buyer paid {past_on_time}/{past_total} past invoices on time ({int(pay_rate*100)}%)"})
        elif pay_rate >= 0.65:
            score += 10
            reasons.append({"type": "neutral", "text": f"Buyer paid {past_on_time}/{past_total} on time ({int(pay_rate*100)}%) — mixed"})
        elif pay_rate >= 0.45:
            score -= 10
            reasons.append({"type": "negative", "text": f"Buyer paid only {past_on_time}/{past_total} on time ({int(pay_rate*100)}%)"})
        else:
            score -= 25
            reasons.append({"type": "negative", "text": f"Buyer paid only {past_on_time}/{past_total} on time ({int(pay_rate*100)}%) — poor payer"})
    else:
        score -= 5
        reasons.append({"type": "negative", "text": "No payment history for this buyer-supplier pair"})
    
    # --- SIGNAL 2: ITC claim (±15 points) ---
    itc = str(invoice.get("itc_claimed_by_buyer", "No")).strip().lower()
    if itc in ("yes", "true", "1"):
        score += 15
        reasons.append({"type": "positive", "text": "Buyer claimed ITC (GSTR-2B) — invoice formally accepted"})
    else:
        score -= 12
        reasons.append({"type": "negative", "text": "ITC not claimed — buyer may not have accepted this invoice"})
    
    # --- SIGNAL 3: Average days late (±12 points) ---
    avg_late = int(invoice.get("buyer_avg_days_late", 30))
    if avg_late <= 10:
        score += 12
        reasons.append({"type": "positive", "text": f"Buyer pays ~{avg_late} days past due — prompt"})
    elif avg_late <= 25:
        score += 4
        reasons.append({"type": "neutral", "text": f"Buyer pays ~{avg_late} days late — moderate"})
    elif avg_late <= 45:
        score -= 8
        reasons.append({"type": "negative", "text": f"Buyer pays ~{avg_late} days late — significant delay"})
    else:
        score -= 12
        reasons.append({"type": "negative", "text": f"Buyer pays ~{avg_late} days late — severe delay"})
    
    # --- SIGNAL 4: E-way bill present (±10 points) ---
    eway = str(invoice.get("eway_bill_present", "No")).strip().lower()
    if eway in ("yes", "true", "1"):
        score += 8
        ewb_num = str(invoice.get("eway_bill_number", "")).split(".")[0]  # handles pandas float coercion
        reasons.append({"type": "positive", "text": f"E-way bill confirmed (EWB {ewb_num[:6]}...) — dispatch verified"})
    else:
        score -= 10
        reasons.append({"type": "negative", "text": "No e-way bill — dispatch not independently confirmed"})
    
    # --- SIGNAL 5: E-way bill CLOSURE (NEW — +7 / -3 points) ---
    ewb_closed = str(invoice.get("eway_bill_closed", "No")).strip().lower()
    if eway in ("yes", "true", "1"):  # Only relevant if EWB exists
        if ewb_closed in ("yes", "true", "1"):
            score += 7
            closure_date = invoice.get("ewb_closure_date", "")
            reasons.append({"type": "positive", "text": f"E-way bill CLOSED on {closure_date} — delivery confirmed (GSTN Aug 2026)"})
        else:
            score -= 3
            reasons.append({"type": "neutral", "text": "E-way bill not closed — delivery not formally confirmed"})
    
    # --- SIGNAL 6: E-invoice IRN (±8 points) ---
    irn_raw = invoice.get("irn", "")
    irn = "" if (irn_raw is None or (isinstance(irn_raw, float) and irn_raw != irn_raw)) else str(irn_raw).strip()
    if len(irn) == 64:  # Real IRN is a 64-char SHA256 hash
        score += 8
        reasons.append({"type": "positive", "text": f"Valid IRN ({irn[:8]}...) — invoice government-verified"})
    elif irn and len(irn) > 0:
        score += 4
        reasons.append({"type": "neutral", "text": "IRN present but format unclear"})
    else:
        score -= 6
        reasons.append({"type": "negative", "text": "No IRN — invoice not registered with IRP"})
    
    # --- SIGNAL 7: Buyer GSTR-3B filing pattern (NEW — ±6 points) ---
    filing = str(invoice.get("buyer_gstr3b_filing", "unknown")).strip().lower()
    if filing == "on_time":
        score += 6
        reasons.append({"type": "positive", "text": "Buyer files GSTR-3B on time — financially disciplined"})
    elif filing == "late":
        score -= 4
        reasons.append({"type": "negative", "text": "Buyer files GSTR-3B late — possible cash stress"})
    elif filing in ("very_late", "not_filed"):
        score -= 6
        reasons.append({"type": "negative", "text": "Buyer GSTR-3B severely delayed — strong distress signal"})
    
    # Clamp
    score = max(2, min(98, score))
    
    # Risk band
    if score >= 70:
        band = "High Trust"
        recommendation = "Low risk. Suitable for financing at standard rates."
    elif score >= 50:
        band = "Watch"
        recommendation = "Moderate risk. Consider higher holdback or closer monitoring."
    else:
        band = "High Risk"
        recommendation = "High risk. Significant warning signals. Finance with caution or decline."
    
    return {
        "score": score,
        "band": band,
        "reasons": reasons,
        "recommendation": recommendation
    }


def score_batch(invoices: list) -> list:
    results = []
    for inv in invoices:
        result = score_invoice(inv)
        result["invoice"] = inv
        results.append(result)
    return results


def get_separation_stats(scored_results: list) -> dict:
    bands = {
        "High Risk": {"total": 0, "defaulted": 0, "scores": []},
        "Watch": {"total": 0, "defaulted": 0, "scores": []},
        "High Trust": {"total": 0, "defaulted": 0, "scores": []},
    }
    
    for r in scored_results:
        band = r["band"]
        bands[band]["total"] += 1
        bands[band]["scores"].append(r["score"])
        outcome = str(r["invoice"].get("outcome", "")).strip().lower()
        if outcome in ("defaulted", "default", "bad", "npa", "loss"):
            bands[band]["defaulted"] += 1
    
    for band_name, data in bands.items():
        if data["total"] > 0:
            data["default_rate"] = round(100 * data["defaulted"] / data["total"], 1)
            data["avg_score"] = round(sum(data["scores"]) / len(data["scores"]), 1)
        else:
            data["default_rate"] = 0
            data["avg_score"] = 0
    
    total_defaults = sum(d["defaulted"] for d in bands.values())
    low_band_defaults = bands["High Risk"]["defaulted"]
    
    return {
        "bands": bands,
        "total_invoices": sum(d["total"] for d in bands.values()),
        "total_defaults": total_defaults,
        "defaults_caught_in_low_band": low_band_defaults,
        "catch_rate": round(100 * low_band_defaults / total_defaults, 1) if total_defaults > 0 else 0,
    }
