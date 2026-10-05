"""Record a pre-metric implementation repair without changing analysis locks."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

out = Path(__file__).resolve().parent
assert not (out / 'temporal_results.json').exists()
assert not (out / 'temporal_repair_01.json').exists()
cutoff = json.loads((out / 'temporal_cutoff_lock.json').read_text(encoding='utf-8'))
fit = json.loads((out / 'temporal_fit_lock.json').read_text(encoding='utf-8'))
record = {
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'stage_of_failure': 'Checkpoint boundary reconstruction, before temporal predictions or losses.',
    'error': 'TypeError: boolean value of NA is ambiguous; pandas nullable string comparison with shifted first row.',
    'repair': 'Fill the initial missing episode-boundary Boolean with True, then convert to NumPy bool. Resume from identical saved cutoff/model/reference and verify hashes/equality; do not refit or rewrite original locks.',
    'statistical_change': False,
    'original_script_sha256': cutoff['script_sha256'],
    'repaired_script_sha256': hashlib.sha256((out / 'temporal_check.py').read_bytes()).hexdigest(),
    'frozen_model_sha256': fit['model_sha256'],
    'frozen_reference_sha256': fit['reference_sha256'],
    'cutoff': cutoff['cutoff'],
    'temporal_outcomes_seen_before_repair': False,
}
(out / 'temporal_repair_01.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2))
