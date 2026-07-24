#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Direct BeatFlow CLI entrypoint for an environment with dependencies installed."""

from beatflow_core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
