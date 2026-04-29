#!/usr/bin/env python3
from __future__ import annotations

import json

from board_cache import sync_cache


if __name__ == "__main__":
    print(json.dumps(sync_cache(), ensure_ascii=False, indent=2))
