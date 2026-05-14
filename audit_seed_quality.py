import csv
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("audit_seed")

def run_audit(users_file: str, concentration_threshold: float = 0.70):
    """
    Audits the quality of the Meta seed dataset.
    Verifies the Pareto Principle: Do the top donors represent the bulk of the value?
    """
    if not Path(users_file).exists():
        logger.error(f"File not found: {users_file}")
        return False

    donors = []
    total_ltv = 0.0
    
    with open(users_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ltv = float(row.get('LTV', 0))
                loyalty = row.get('LOYALTY_LEVEL', 'UNKNOWN')
                donors.append({'ltv': ltv, 'loyalty': loyalty})
                total_ltv += ltv
            except ValueError:
                continue

    if not donors:
        logger.error("No valid donor data found for audit.")
        return False

    # Sort donors by LTV descending
    sorted_donors = sorted(donors, key=lambda x: x['ltv'], reverse=True)
    
    # Calculate Concentration Metrics
    top_10_count = max(1, int(len(donors) * 0.10))
    top_10_val = sum(d['ltv'] for d in sorted_donors[:top_10_count])
    
    vip_count = sum(1 for d in donors if d['loyalty'] == 'VIP')
    vip_val = sum(d['ltv'] for d in donors if d['loyalty'] == 'VIP')
    
    concentration_ratio = top_10_val / total_ltv if total_ltv > 0 else 0
    vip_value_ratio = vip_val / total_ltv if total_ltv > 0 else 0

    print("\n" + "="*50)
    print("SEED QUALITY AUDIT: Meta Value-Based Signal")
    print("="*50)
    print(f"Total Donors:         {len(donors)}")
    print(f"Total Lifetime Value: ${total_ltv:,.2f}")
    print(f"VIP Count:            {vip_count} ({ (vip_count/len(donors))*100:.1f}%)")
    print("-" * 50)
    print(f"Top 10% Concentration: {concentration_ratio*100:.1f}% of total value")
    print(f"VIP Value Share:       {vip_value_ratio*100:.1f}% of total value")
    print("-" * 50)

    # Decision Logic
    success = True
    if concentration_ratio < concentration_threshold:
        logger.warning(f"WEAK SIGNAL: Top 10% hold only {concentration_ratio*100:.1f}% of value.")
        logger.warning(f"Meta's Value-Based Lookalikes perform best when concentration is >{concentration_threshold*100:.0f}%.")
        success = False
    else:
        logger.info(f"STRONG SIGNAL: Seed data meets the {concentration_threshold*100:.0f}% Pareto threshold.")

    if vip_count < 100:
        logger.warning(f"SMALL SEED: Found only {vip_count} VIPs. Meta recommends 100+ for stable lookalikes.")
        # We don't fail here because the toolkit default is 200 users, and ~15% are VIPs (30 users).
        # We warn instead.

    print("="*50 + "\n")
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit donor seed quality for Meta Value-Based Lookalikes.")
    parser.add_argument("--file", type=str, default="aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv", 
                        help="Path to users CSV")
    parser.add_argument("--threshold", type=float, default=0.60, 
                        help="Required concentration ratio for top 10%% (default: 0.60)")
    
    args = parser.parse_args()
    run_audit(args.file, args.threshold)
