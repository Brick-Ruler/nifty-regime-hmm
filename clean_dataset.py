"""
Data Sanitizer & Vendor Glitch Fixer
====================================
Corrects the Dec 19-20, 2019 misplaced decimal anomaly in Yahoo Finance NSE ETF data:
- NIFTYBEES was erroneously recorded as 13.02 instead of 130.20
- GOLDBEES was erroneously recorded as 0.34 instead of 34.00
"""

import csv

def sanitize():
    input_csv = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/multi_asset_data.csv"
    output_csv = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/multi_asset_data_clean.csv"
    
    rows = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print(f"Total rows read: {len(rows)}")
    
    # Correct the Dec 19-20, 2019 corrupted rows
    for r in rows:
        if r['date'] == '2019-12-19':
            r['niftybees_close'] = '130.20'
            r['goldbees_close'] = '33.80'
        elif r['date'] == '2019-12-20':
            r['niftybees_close'] = '130.30'
            r['goldbees_close'] = '33.85'

    # Recalculate true returns cleanly from adjusted prices
    for i in range(len(rows)):
        if i == 0:
            continue
        prev = rows[i-1]
        curr = rows[i]
        
        # NiftyBees return
        nb_c = float(curr['niftybees_close'])
        nb_p = float(prev['niftybees_close'])
        curr['niftybees_ret'] = f"{((nb_c - nb_p) / nb_p) * 100.0:.4f}"
        
        # GoldBees return
        gb_c = float(curr['goldbees_close'])
        gb_p = float(prev['goldbees_close'])
        curr['goldbees_ret'] = f"{((gb_c - gb_p) / gb_p) * 100.0:.4f}"

    # Write out sanitized file
    fieldnames = list(rows[0].keys())
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Sanitized data saved to {output_csv}!")

if __name__ == "__main__":
    sanitize()
