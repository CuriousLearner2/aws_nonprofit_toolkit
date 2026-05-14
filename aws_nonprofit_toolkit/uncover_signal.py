import pandas as pd
import numpy as np

def analyze_bias(file_path):
    print(f"--- Analyzing {file_path} ---")
    df = pd.read_csv(file_path)
    
    # Convert USER_ID from 'user_123' string to integer 123
    df['user_num'] = df['USER_ID'].str.replace('user_', '').astype(int)
    
    # Split users into the two groups we created
    # Group A: 0-499 (Biased)
    # Group B: 500-1999 (Neutral)
    group_a = df[df['user_num'] < 500]
    group_b = df[df['user_num'] >= 500]
    
    print(f"Total Interactions: {len(df)}")
    print(f"Group A (Users 0-499) Interactions: {len(group_a)}")
    print(f"Group B (Users 500-1999) Interactions: {len(group_b)}")
    print("-" * 30)

    # Calculate preference percentages for each group
    pref_a = group_a['ITEM_ID'].value_counts(normalize=True) * 100
    pref_b = group_b['ITEM_ID'].value_counts(normalize=True) * 100

    results = pd.DataFrame({
        'Group A % (Biased)': pref_a,
        'Group B % (Neutral)': pref_b
    }).fillna(0)
    
    print("Item Preference by Group (Percentages):")
    print(results.round(2))
    print("-" * 30)
    
    # Conclusion logic
    diff = (results['Group A % (Biased)'] - results['Group B % (Neutral)']).abs()
    top_diff_item = diff.idxmax()
    
    print(f"MATH REVEALS: Group A has a disproportionate interest in '{top_diff_item}'.")
    print(f"Difference: {diff.max():.2f}% higher than the neutral group.")
    print("\nThis is the 'Signal' an ML model would consume to make recommendations.")

if __name__ == "__main__":
    analyze_bias("aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv")
