import csv
from collections import Counter

def analyze_bias(file_path):
    print(f"--- Analyzing {file_path} (Pure Python) ---")
    
    group_a_items = []
    group_b_items = []
    
    with open(file_path, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row['USER_ID']
            item_id = row['ITEM_ID']
            user_num = int(user_id.replace('user_', ''))
            
            if user_num < 500:
                group_a_items.append(item_id)
            else:
                group_b_items.append(item_id)
    
    total_a = len(group_a_items)
    total_b = len(group_b_items)
    
    counts_a = Counter(group_a_items)
    counts_b = Counter(group_b_items)
    
    all_items = sorted(list(set(group_a_items) | set(group_b_items)))
    
    print(f"Total Interactions: {total_a + total_b}")
    print(f"Group A (Users 0-499) Interactions: {total_a}")
    print(f"Group B (Users 500-1999) Interactions: {total_b}")
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
    print(f"MATH REVEALS: Group A has a disproportionate interest in '{top_diff_item}'.")
    print(f"Difference: {max_diff:.2f}% shift compared to the neutral group.")
    print("\nThis statistical 'bulge' is exactly what Amazon Personalize detects")
    print("to know that it should recommend certain items to specific user types.")

if __name__ == "__main__":
    analyze_bias("aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv")
