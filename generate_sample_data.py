import csv
import random
import os
import hashlib
import datetime

"""
Setu Sample Data Generator — Version 2
========================================
Now generates data that matches REAL government document formats:

1. GST E-Invoice (Form GST INV-01) — ~50 mandatory fields, JSON schema
   Key fields: IRN (64-char SHA256 hash), supplier GSTIN, buyer GSTIN,
   document type/number/date, HSN codes, taxable value, tax amounts,
   total invoice value, QR code data

2. E-Way Bill (Form GST EWB-01) — Part A + Part B
   Part A: supplier/buyer GSTIN, document details, HSN, value, transport mode
   Part B: vehicle number, transporter ID/document number
   NEW (Aug 1 2026): Closure status — delivery confirmed or not

3. GSTR-2B fields — ITC claim status (buyer accepted the invoice?)

4. Bank transaction fields — payment dates, amounts (via Account Aggregator)

All GSTINs follow the real 15-character format:
  [2-digit state code][10-char PAN][1-char entity][Z][checksum]
  State 27 = Maharashtra (Pune cluster)

All IRNs follow real format: 64-character SHA256 hash

All EWB numbers: 12-digit numeric

HSN codes: real codes for auto components
"""

random.seed(42)

# Real HSN codes for auto components
HSN_CODES = {
    "brackets": "7326",      # Articles of iron/steel
    "stampings": "7326",
    "forgings": "7207",      # Semi-finished products of iron
    "castings": "7325",      # Cast articles of iron/steel
    "fasteners": "7318",     # Screws, bolts, nuts
    "bushings": "8483",      # Transmission shafts, bearings
    "gaskets": "8484",       # Gaskets and similar joints
    "springs": "7320",       # Springs of iron or steel
}

PRODUCTS = list(HSN_CODES.keys())

# Realistic buyer profiles
buyers = [
    {
        "name": "Anchor Auto Components Pvt Ltd",
        "gstin": "27AABCA1234B1Z5",
        "pan": "AABCA1234B",
        "state": "Maharashtra",
        "city": "Chakan",
        "pay_rate": 0.95,
        "avg_late_days": 8,
        "itc_claim_rate": 0.95,
        "eway_rate": 1.0,
        "ewb_closure_rate": 0.85,  # NEW: how often they close the EWB
        "turnover_trend": "growing",
        "default_prob": 0.02,
        "gstr3b_filing": "on_time",
    },
    {
        "name": "Metro Forgings & Stampings Ltd",
        "gstin": "27AABCM5678D1Z3",
        "pan": "AABCM5678D",
        "state": "Maharashtra",
        "city": "Pimpri-Chinchwad",
        "pay_rate": 0.85,
        "avg_late_days": 18,
        "itc_claim_rate": 0.88,
        "eway_rate": 1.0,
        "ewb_closure_rate": 0.70,
        "turnover_trend": "stable",
        "default_prob": 0.05,
        "gstr3b_filing": "on_time",
    },
    {
        "name": "Reliable Engineering Works",
        "gstin": "27AABCR9012F1Z1",
        "pan": "AABCR9012F",
        "state": "Maharashtra",
        "city": "Pune",
        "pay_rate": 0.80,
        "avg_late_days": 22,
        "itc_claim_rate": 0.82,
        "eway_rate": 0.95,
        "ewb_closure_rate": 0.60,
        "turnover_trend": "stable",
        "default_prob": 0.08,
        "gstr3b_filing": "on_time",
    },
    {
        "name": "Kisan Motors India Pvt Ltd",
        "gstin": "27AABCK3456H1Z9",
        "pan": "AABCK3456H",
        "state": "Maharashtra",
        "city": "Aurangabad",
        "pay_rate": 0.45,
        "avg_late_days": 55,
        "itc_claim_rate": 0.40,
        "eway_rate": 0.70,
        "ewb_closure_rate": 0.20,
        "turnover_trend": "declining",
        "default_prob": 0.35,
        "gstr3b_filing": "late",
    },
    {
        "name": "Shakti Castings & Alloys",
        "gstin": "27AABCS7890J1Z7",
        "pan": "AABCS7890J",
        "state": "Maharashtra",
        "city": "Pune",
        "pay_rate": 0.50,
        "avg_late_days": 48,
        "itc_claim_rate": 0.45,
        "eway_rate": 0.75,
        "ewb_closure_rate": 0.25,
        "turnover_trend": "declining",
        "default_prob": 0.30,
        "gstr3b_filing": "late",
    },
    {
        "name": "Verma Udyog Pvt Ltd",
        "gstin": "27AABCV2345L1Z5",
        "pan": "AABCV2345L",
        "state": "Maharashtra",
        "city": "Chakan",
        "pay_rate": 0.38,
        "avg_late_days": 62,
        "itc_claim_rate": 0.35,
        "eway_rate": 0.60,
        "ewb_closure_rate": 0.10,
        "turnover_trend": "declining",
        "default_prob": 0.42,
        "gstr3b_filing": "very_late",
    },
    {
        "name": "Precision Parts Manufacturing",
        "gstin": "27AABCP6789N1Z3",
        "pan": "AABCP6789N",
        "state": "Maharashtra",
        "city": "Chakan",
        "pay_rate": 0.90,
        "avg_late_days": 12,
        "itc_claim_rate": 0.92,
        "eway_rate": 1.0,
        "ewb_closure_rate": 0.80,
        "turnover_trend": "growing",
        "default_prob": 0.03,
        "gstr3b_filing": "on_time",
    },
    {
        "name": "National Auto Accessories Ltd",
        "gstin": "27AABCN1234P1Z1",
        "pan": "AABCN1234P",
        "state": "Maharashtra",
        "city": "Nashik",
        "pay_rate": 0.72,
        "avg_late_days": 30,
        "itc_claim_rate": 0.70,
        "eway_rate": 0.90,
        "ewb_closure_rate": 0.50,
        "turnover_trend": "stable",
        "default_prob": 0.12,
        "gstr3b_filing": "on_time",
    },
]

suppliers = [
    {"name": "Shree Ganesh Stampings", "gstin": "27AABCS1111A1Z5", "pan": "AABCS1111A", "cluster": "Pune-Chakan", "udyam": "UDYAM-MH-02-0012345"},
    {"name": "Mahalaxmi Precision Parts", "gstin": "27AABCM2222B1Z3", "pan": "AABCM2222B", "cluster": "Pune-Chakan", "udyam": "UDYAM-MH-02-0023456"},
    {"name": "Jay Bhavani Engineering", "gstin": "27AABCJ3333C1Z1", "pan": "AABCJ3333C", "cluster": "Pimpri-Chinchwad", "udyam": "UDYAM-MH-02-0034567"},
    {"name": "Sai Auto Components", "gstin": "27AABCS4444D1Z9", "pan": "AABCS4444D", "cluster": "Pune-Chakan", "udyam": "UDYAM-MH-02-0045678"},
    {"name": "Gurukrupa Metal Works", "gstin": "27AABCG5555E1Z7", "pan": "AABCG5555E", "cluster": "Chakan", "udyam": "UDYAM-MH-02-0056789"},
]

def generate_irn(supplier_gstin, fin_year, doc_number):
    """Generate IRN like the real IRP does — SHA256 hash of GSTIN+FY+DocNo"""
    raw = f"{supplier_gstin}{fin_year}{doc_number}"
    return hashlib.sha256(raw.encode()).hexdigest()

def generate_ewb_number():
    """12-digit numeric EWB number"""
    return str(random.randint(100000000000, 999999999999))

invoices = []
inv_num = 2401001

for i in range(200):
    supplier = random.choice(suppliers)
    buyer = random.choice(buyers)
    product = random.choice(PRODUCTS)
    hsn = HSN_CODES[product]
    
    # Realistic quantity and unit price for auto components
    quantity = random.choice([500, 1000, 2000, 5000, 10000])
    unit_price = random.choice([15, 25, 35, 45, 65, 85, 120, 180])
    taxable_value = quantity * unit_price
    gst_rate = 18  # Standard GST rate for auto components
    cgst = round(taxable_value * 0.09, 2)  # 9% CGST
    sgst = round(taxable_value * 0.09, 2)  # 9% SGST (intra-state Maharashtra)
    total_value = taxable_value + cgst + sgst
    
    # Invoice date spread across FY 2025-26
    month = random.randint(4, 12)  # Apr-Dec 2025
    day = random.randint(1, 28)
    inv_date = f"2025-{month:02d}-{day:02d}"
    doc_number = f"SI/{inv_num}"
    fin_year = "2025-26"
    
    # Generate real-format IRN
    irn = generate_irn(supplier["gstin"], fin_year, doc_number)
    
    # E-way bill signals
    has_eway = random.random() < buyer["eway_rate"]
    ewb_number = generate_ewb_number() if has_eway else ""
    
    # NEW: EWB closure status (only if EWB exists)
    ewb_closed = False
    ewb_closure_date = ""
    if has_eway:
        ewb_closed = random.random() < buyer["ewb_closure_rate"]
        if ewb_closed:
            closure_day = min(day + random.choice([0, 1]), 28)
            ewb_closure_date = f"2025-{month:02d}-{closure_day:02d}"
    
    # ITC claim by buyer
    itc_claimed = random.random() < buyer["itc_claim_rate"]
    
    # Payment history
    past_paid_on_time = max(0, min(6, int(random.gauss(buyer["pay_rate"] * 6, 0.8))))
    past_total = 6
    days_late = max(0, int(random.gauss(buyer["avg_late_days"], 10)))
    
    # GSTR-3B filing pattern
    gstr3b_filing = buyer["gstr3b_filing"]
    
    # Default probability
    base_prob = buyer["default_prob"]
    if not has_eway: base_prob += 0.08
    if not ewb_closed and has_eway: base_prob += 0.05
    if not itc_claimed: base_prob += 0.08
    if past_paid_on_time <= 2: base_prob += 0.05
    if gstr3b_filing == "late": base_prob += 0.03
    if gstr3b_filing == "very_late": base_prob += 0.06
    
    defaulted = random.random() < base_prob
    
    # Vehicle number (Maharashtra format)
    vehicle = f"MH{random.choice(['12','14','04','02'])}{chr(random.randint(65,90))}{chr(random.randint(65,90))}{random.randint(1000,9999)}"
    
    invoices.append({
        # --- E-Invoice fields (Form GST INV-01) ---
        "invoice_id": doc_number,
        "irn": irn,
        "invoice_date": inv_date,
        "document_type": "INV",
        "supplier_name": supplier["name"],
        "supplier_gstin": supplier["gstin"],
        "supplier_pan": supplier["pan"],
        "supplier_udyam": supplier["udyam"],
        "supplier_cluster": supplier["cluster"],
        "buyer_name": buyer["name"],
        "buyer_gstin": buyer["gstin"],
        "buyer_pan": buyer["pan"],
        "buyer_state": buyer["state"],
        "buyer_city": buyer["city"],
        "product": product,
        "hsn_code": hsn,
        "quantity": quantity,
        "unit_price": unit_price,
        "taxable_value": taxable_value,
        "gst_rate": gst_rate,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "total_invoice_value": total_value,
        
        # --- E-Way Bill fields (Form GST EWB-01) ---
        "eway_bill_number": ewb_number,
        "eway_bill_present": "Yes" if has_eway else "No",
        "eway_bill_date": inv_date if has_eway else "",
        "transport_mode": "Road" if has_eway else "",
        "vehicle_number": vehicle if has_eway else "",
        "eway_bill_closed": "Yes" if ewb_closed else "No",
        "ewb_closure_date": ewb_closure_date,
        
        # --- GSTR-2B / ITC fields ---
        "itc_claimed_by_buyer": "Yes" if itc_claimed else "No",
        
        # --- Buyer behavior signals (from AA bank data) ---
        "buyer_past_on_time": past_paid_on_time,
        "buyer_past_total": past_total,
        "buyer_avg_days_late": days_late,
        "buyer_turnover_trend": buyer["turnover_trend"],
        "buyer_gstr3b_filing": gstr3b_filing,
        
        # --- Outcome (for backtest only) ---
        "outcome": "Defaulted" if defaulted else "Repaid"
    })
    
    inv_num += 1

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_invoices.csv")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=invoices[0].keys())
    writer.writeheader()
    writer.writerows(invoices)

print(f"Generated {len(invoices)} invoices")
print(f"Defaults: {sum(1 for inv in invoices if inv['outcome'] == 'Defaulted')}")
print(f"Repaid: {sum(1 for inv in invoices if inv['outcome'] == 'Repaid')}")
print(f"With EWB closure: {sum(1 for inv in invoices if inv['eway_bill_closed'] == 'Yes')}")
print(f"Saved to {output_path}")
