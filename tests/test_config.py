import pytest
from aws_nonprofit_toolkit.config import SimulationConfig

def test_config_validation_valid():
    """Verify that default config is valid."""
    # Should not raise
    SimulationConfig.validate()

def test_config_validation_invalid_loyalty(monkeypatch):
    """Verify error on invalid loyalty sum."""
    monkeypatch.setattr(SimulationConfig, "LOYALTY_DISTRIBUTION", {'NEW': 0.1})
    with pytest.raises(ValueError, match="LOYALTY_DISTRIBUTION weights must sum to 1.0"):
        SimulationConfig.validate()

def test_config_validation_invalid_bias(monkeypatch):
    """Verify error on invalid bias weight."""
    monkeypatch.setattr(SimulationConfig, "CAUSE_BIAS_WEIGHT", 1.5)
    with pytest.raises(ValueError, match="CAUSE_BIAS_WEIGHT must be between 0.0 and 1.0"):
        SimulationConfig.validate()
