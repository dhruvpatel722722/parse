import json
import os


def load_reference():
    ref_path = "/var/lib/tbench/.reference.json"
    assert os.path.exists(ref_path), f"Reference not found at {ref_path}"
    with open(ref_path) as f:
        return json.load(f)


def load_output():
    out_path = "/app/output/channel_states.txt"
    assert os.path.exists(out_path), f"Output not found at {out_path}"
    with open(out_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    return [int(x) for x in lines]


class TestTelemetryRecovery:
    def test_output_exists(self):
        assert os.path.exists("/app/output/channel_states.txt")

    def test_correct_line_count(self):
        output = load_output()
        assert len(output) == 64, f"Expected 64 lines, got {len(output)}"

    def test_values_in_range(self):
        output = load_output()
        for i, val in enumerate(output):
            assert 0 <= val <= 255, f"Channel {i} state {val} out of range [0,255]"

    def test_exact_channel_states(self):
        ref = load_reference()
        output = load_output()
        expected = ref["channel_states"]
        assert output == expected, (
            f"Channel states mismatch. "
            f"First diff at channel {next(i for i in range(64) if output[i] != expected[i])}"
        )
