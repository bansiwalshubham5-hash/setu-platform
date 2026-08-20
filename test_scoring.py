"""
Quick test: does the scoring engine actually separate defaults from repaid invoices?
Run this BEFORE building any UI.
"""
import csv
from scoring_engine import score_invoice, score_batch, get_separation_stats

# Load sample data
with open("data/sample_invoices.csv", "r") as f:
    reader = csv.DictReader(f)
    invoices = list(reader)

print(f"Loaded {len(invoices)} invoices")
print(f"Defaults: {sum(1 for i in invoices if i['outcome'] == 'Defaulted')}")
print(f"Repaid: {sum(1 for i in invoices if i['outcome'] == 'Repaid')}")
print()

# Score all invoices
scored = score_batch(invoices)

# Check separation
stats = get_separation_stats(scored)

print("=" * 60)
print("SEPARATION TEST RESULTS")
print("=" * 60)
print()

for band_name in ["High Risk", "Watch", "High Trust"]:
    data = stats["bands"][band_name]
    print(f"{band_name}:")
    print(f"  Invoices: {data['total']}")
    print(f"  Defaults: {data['defaulted']}")
    print(f"  Default rate: {data['default_rate']}%")
    print(f"  Avg score: {data['avg_score']}")
    print()

print(f"Total defaults: {stats['total_defaults']}")
print(f"Caught in High Risk band: {stats['defaults_caught_in_low_band']}")
print(f"Catch rate: {stats['catch_rate']}%")
print()

# The verdict
if stats["catch_rate"] >= 50:
    print("PASS — Defaults concentrate in the low-score band.")
    print("The score separates. This is worth showing to an NBFC.")
else:
    print("FAIL — Defaults are spread across all bands.")
    print("The score does NOT separate well. Fix the weights before building UI.")

# Show a few example scores
print()
print("=" * 60)
print("EXAMPLE SCORED INVOICES")
print("=" * 60)
for r in sorted(scored, key=lambda x: x["score"])[:3]:
    inv = r["invoice"]
    print(f"\n{inv['invoice_id']} | {inv['buyer_name']} | ₹{int(float(inv.get('total_invoice_value', 0))):,}")
    print(f"  Score: {r['score']} | Band: {r['band']} | Outcome: {inv['outcome']}")
    for reason in r["reasons"]:
        symbol = "✓" if reason["type"] == "positive" else ("✕" if reason["type"] == "negative" else "~")
        print(f"  {symbol} {reason['text']}")

print()
for r in sorted(scored, key=lambda x: x["score"], reverse=True)[:3]:
    inv = r["invoice"]
    print(f"\n{inv['invoice_id']} | {inv['buyer_name']} | ₹{int(float(inv.get('total_invoice_value', 0))):,}")
    print(f"  Score: {r['score']} | Band: {r['band']} | Outcome: {inv['outcome']}")
    for reason in r["reasons"]:
        symbol = "✓" if reason["type"] == "positive" else ("✕" if reason["type"] == "negative" else "~")
        print(f"  {symbol} {reason['text']}")
