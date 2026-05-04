import pytest
import csv
import os
from pathlib import Path
from aws_nonprofit_toolkit.generate_datasets import generate_small_nonprofit, generate_large_nonprofit
from aws_nonprofit_toolkit.config import SimulationConfig

def test_small_dataset_schema(tmp_path):
    """Verify schema and content of the small nonprofit dataset."""
    generate_small_nonprofit(tmp_path, SimulationConfig.SMALL_USER_COUNT)
    
    users_file = tmp_path / 'small_nonprofit_users.csv'
    assert users_file.exists()
    
    with open(users_file, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert 'LOYALTY_LEVEL' in headers
        assert 'INTEREST_TAG' in headers
        
        # Check first row
        row = next(reader)
        assert row['USER_ID'].startswith('user_')
        assert row['LOYALTY_LEVEL'] in SimulationConfig.get_loyalty_levels()

def test_large_dataset_signal_integrity(tmp_path):
    """Verify that the large dataset meets minimum requirements for Amazon Personalize."""
    generate_large_nonprofit(tmp_path, 2000, 0.25)
    
    interactions_file = tmp_path / 'large_nonprofit_interactions.csv'
    assert interactions_file.exists()
    
    line_count = 0
    with open(interactions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_count += 1
            # Verify timestamp is integer
            assert int(row['TIMESTAMP']) > 0
            # Verify event types
            assert row['EVENT_TYPE'] in ['VIEW', 'DONATE', 'SIGN_UP']
            
    assert line_count >= 1000 # Minimum requirement
