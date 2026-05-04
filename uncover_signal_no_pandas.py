import csv
from collections import Counter

def analyze_bias(file_path: str):
    """
    Analyzes donor interaction bias using a memory-efficient streaming approach.
    Scales to millions of records by avoiding loading the full CSV into RAM.
    """
    print(f"--- Analyzing {file_path} (Streaming Mode) ---")
    
    counts_a = Counter()
    counts_b = Counter()
    total_a = 0
    total_b = 0
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row.get('USER_ID', '')
                item_id = row.get('ITEM_ID', '')
                
                # Logic: Users 0-499 are Group A (Biased)
                try:
                    user_num = int(user_id.replace('user_', ''))
                    if user_num < 500:
                        counts_a[item_id] += 1
                        total_a += 1
                    else:
                        counts_b[item_id] += 1
                        total_b += 1
                except ValueError:
                    continue # Skip invalid user IDs

        if total_a == 0 or total_b == 0:
            print("Error: One or more groups have zero interactions.")
            return

        all_items = sorted(list(set(counts_a.keys()) | set(counts_b.keys())))
        
        print(f"Total Interactions Analyzed: {total_a + total_b}")
        print(f"Group A (Biased) Count: {total_a}")
        print(f"Group B (Baseline) Count: {total_b}")
        print("-" * 30)
        print(f"{'Item ID':<20} | {'Group A %':<10} | {'Group B %':<10}")
        print("-" * 45)
        
        max_diff = 0
        top_diff_item = ""

        for item in all_items:
            perc_a = (counts_a[item] / total_a) * 100
            perc_b = (counts_b[item] / total_b) * 100
            diff = perc_a - perc_b
            
            if abs(diff) > max_diff:
                max_diff = abs(diff)
                top_diff_item = item
                
            print(f"{item:<20} | {perc_a:>8.2f}% | {perc_b:>8.2f}%")

        print("-" * 30)
        print(f"SIGNAL DETECTED: Group A shows a bias toward '{top_diff_item}'.")
        print(f"Shift Intensity: {max_diff:.2f}%")
        print("\nSCALABILITY NOTE: This analysis used streaming (line-by-line) to minimize memory footprint.")

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    analyze_bias("aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv")
