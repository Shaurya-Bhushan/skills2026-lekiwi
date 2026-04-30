#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

LEADER_ARM_PORT="${1:-auto}"
SIM_REPO="${2:-}"

if [[ -n "$SIM_REPO" ]]; then
  python -m skills2026.cli sim_leader --sim-repo "$SIM_REPO" --leader-arm-port "$LEADER_ARM_PORT"
else
  python -m skills2026.cli sim_leader --leader-arm-port "$LEADER_ARM_PORT"
fi
