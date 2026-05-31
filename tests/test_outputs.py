import json
import os
import pytest


def load_reference():
    """Load the reference answer."""
    ref_path = "/var/lib/tbench/.reference.json"
    assert os.path.exists(ref_path), f"Reference file not found at {ref_path}"
    with open(ref_path) as f:
        return json.load(f)


def load_output():
    """Load the agent's output."""
    out_path = "/app/output/install_order.txt"
    assert os.path.exists(out_path), f"Output file not found at {out_path}"
    with open(out_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


class TestPackageResolver:
    def test_output_exists(self):
        """Check that output file was created."""
        assert os.path.exists("/app/output/install_order.txt"), \
            "Output file /app/output/install_order.txt not found"

    def test_correct_package_count(self):
        """Check that the correct number of packages are in the output."""
        ref = load_reference()
        output = load_output()
        expected_count = ref["total_installed"]
        assert len(output) == expected_count, \
            f"Expected {expected_count} packages, got {len(output)}"

    def test_no_skipped_packages_in_output(self):
        """Check that conflict-skipped packages are not in the output."""
        ref = load_reference()
        output = load_output()
        for pkg in ref["skipped"]:
            assert pkg not in output, \
                f"Skipped package '{pkg}' should not be in output"

    def test_exact_install_order(self):
        """Check that the install order matches exactly."""
        ref = load_reference()
        output = load_output()
        expected = ref["install_order"]
        assert output == expected, \
            f"Install order mismatch.\nExpected: {expected[:10]}...\nGot:      {output[:10]}..."

    def test_dependency_ordering(self):
        """Check that dependencies come before their dependents in the output."""
        ref = load_reference()
        output = load_output()
        # Every package in output should appear after all its resolved deps
        position = {pkg: i for i, pkg in enumerate(output)}
        # Load deps from reference to verify ordering
        expected = ref["install_order"]
        pos_expected = {pkg: i for i, pkg in enumerate(expected)}
        for pkg in output:
            if pkg in pos_expected:
                assert position[pkg] == pos_expected[pkg], \
                    f"Package '{pkg}' at wrong position: expected {pos_expected[pkg]}, got {position[pkg]}"
