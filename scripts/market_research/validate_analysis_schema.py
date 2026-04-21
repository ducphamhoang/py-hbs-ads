from __future__ import annotations

import argparse
import json
from pathlib import Path

from hbs_ads.features.market_research.validators import validate_analysis_payload


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate a market research analysis JSON payload.')
    parser.add_argument('json_path', help='Path to JSON file to validate')
    args = parser.parse_args()

    path = Path(args.json_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding='utf-8'))
    errors = validate_analysis_payload(payload)
    if errors:
        print(json.dumps({'valid': False, 'errors': errors}, indent=2))
        return 1
    print(json.dumps({'valid': True, 'errors': []}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
