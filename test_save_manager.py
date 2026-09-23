import json
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.save_manager import (
    load_high_scores,
    save_high_score,
    calculate_checksum,
    get_machine_id,
    _get_default_data,
    CURRENT_SCHEMA_VERSION,
)


def test_fresh_save():
    """Test that a fresh save loads defaults correctly."""
    print("Test: Fresh save...")
    data = load_high_scores()
    assert data["sliding_high_score"] == 0
    assert data["balancing_high_streak"] == 0
    assert data["naming_high_streak"] == 0
    assert data["periodic_trends_high_streak"] == 0
    assert data["schema_version"] == CURRENT_SCHEMA_VERSION
    expected = calculate_checksum(0, 0, 0, 0)
    assert data["checksum"] == expected
    print("  PASS")


def test_legacy_migration():
    """Test migration from v1 (molar_mass) to v2 (periodic_trends)."""
    print("Test: Legacy v1 -> v2 migration...")
    
    # Create a valid legacy save
    sliding = 1000
    balancing = 5
    naming = 3
    molar_mass = 7
    machine_id = get_machine_id()
    legacy_raw = f"{sliding}-{balancing}-{naming}-{molar_mass}-PeriodicPuzzleSecretSalt10910(!)#*-{machine_id}"
    legacy_checksum = __import__("hashlib").sha256(legacy_raw.encode()).hexdigest()

    legacy_data = {
        "sliding_high_score": sliding,
        "balancing_high_streak": balancing,
        "naming_high_streak": naming,
        "molar_mass_high_streak": molar_mass,
        "checksum": legacy_checksum,
        # No schema_version = defaults to 1
    }

    # Write to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "highscores.json"
        with open(save_path, "w") as f:
            json.dump(legacy_data, f)

        # Temporarily override save_dir
        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            data = load_high_scores()
        finally:
            sm.save_dir = original_save_dir

    assert data["sliding_high_score"] == sliding
    assert data["balancing_high_streak"] == balancing
    assert data["naming_high_streak"] == naming
    assert data["periodic_trends_high_streak"] == molar_mass
    assert data["schema_version"] == 2
    expected = calculate_checksum(sliding, balancing, naming, molar_mass)
    assert data["checksum"] == expected
    print("  PASS")


def test_invalid_legacy_checksum_rejected():
    """Test that corrupted legacy save is rejected and reset."""
    print("Test: Invalid legacy checksum rejected...")
    
    legacy_data = {
        "sliding_high_score": 1000,
        "balancing_high_streak": 5,
        "naming_high_streak": 3,
        "molar_mass_high_streak": 7,
        "checksum": "invalid_checksum",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "highscores.json"
        with open(save_path, "w") as f:
            json.dump(legacy_data, f)

        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            data = load_high_scores()
        finally:
            sm.save_dir = original_save_dir

    # Should reset to defaults
    assert data["sliding_high_score"] == 0
    assert data["schema_version"] == CURRENT_SCHEMA_VERSION
    print("  PASS")


def test_save_and_load_roundtrip():
    """Test saving and loading a score."""
    print("Test: Save/load roundtrip...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            # Save a score
            save_high_score("sliding", 5000)
            save_high_score("balancing", 10)
            save_high_score("naming", 8)
            save_high_score("periodic_trends", 12)

            # Load and verify
            data = load_high_scores()
            assert data["sliding_high_score"] == 5000
            assert data["balancing_high_streak"] == 10
            assert data["naming_high_streak"] == 8
            assert data["periodic_trends_high_streak"] == 12
            assert data["schema_version"] == CURRENT_SCHEMA_VERSION
        finally:
            sm.save_dir = original_save_dir

    print("  PASS")


def test_save_only_updates_if_higher():
    """Test that save_high_score only updates if new score is higher."""
    print("Test: Save only updates if higher...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            save_high_score("sliding", 1000)
            save_high_score("sliding", 500)  # Lower, should not update
            data = load_high_scores()
            assert data["sliding_high_score"] == 1000

            save_high_score("sliding", 2000)  # Higher, should update
            data = load_high_scores()
            assert data["sliding_high_score"] == 2000
        finally:
            sm.save_dir = original_save_dir

    print("  PASS")


def test_corrupted_json_resets():
    """Test that corrupted JSON resets to defaults."""
    print("Test: Corrupted JSON resets...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "highscores.json"
        with open(save_path, "w") as f:
            f.write("{ not valid json }")

        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            data = load_high_scores()
        finally:
            sm.save_dir = original_save_dir

    default = _get_default_data()
    assert data == default
    print("  PASS")


def test_checksum_validation():
    """Test that tampered checksum is detected."""
    print("Test: Checksum validation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import utils.save_manager as sm
        original_save_dir = sm.save_dir
        sm.save_dir = Path(tmpdir)
        try:
            save_high_score("sliding", 1000)
            
            # Tamper with the file
            save_path = Path(tmpdir) / "highscores.json"
            with open(save_path, "r") as f:
                data = json.load(f)
            data["sliding_high_score"] = 999999  # Tamper
            # Don't update checksum
            with open(save_path, "w") as f:
                json.dump(data, f)

            # Should reset
            loaded = load_high_scores()
            assert loaded["sliding_high_score"] == 0
        finally:
            sm.save_dir = original_save_dir

    print("  PASS")


if __name__ == "__main__":
    test_fresh_save()
    test_legacy_migration()
    test_invalid_legacy_checksum_rejected()
    test_save_and_load_roundtrip()
    test_save_only_updates_if_higher()
    test_corrupted_json_resets()
    test_checksum_validation()
    print("\nAll tests passed!")