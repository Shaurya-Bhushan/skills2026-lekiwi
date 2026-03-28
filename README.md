# skills2026-lekiwi

Plug-and-play LeKiwi tooling for the 2026 Skills Ontario ECU workflow.

This package adds:

- a beginner-friendly setup UI
- profile-based hardware discovery and saved robot configs
- doctor/preflight checks
- two-camera runtime budgeting for a Pi 5 4 GB
- OpenCV perception with front-camera coarse targeting and wrist-camera precision assist
- scripted ECU primitives with graceful fallback to front-only mode
- an optional SmolVLA backend for fine-tuned LeKiwi policies
- teleop / record / replay helpers that stay close to official LeRobot workflows

## What you need

- Python 3.12+
- a working LeRobot environment
- LeKiwi robot access
- front and wrist RGB cameras
- optional: a fine-tuned SmolVLA checkpoint

This project works best when either:

- `lerobot` is already installed in your Python environment, or
- this repo is placed beside a sibling `lerobot/` checkout

## Install

```bash
git clone https://github.com/YOUR_USERNAME/skills2026-lekiwi.git
cd skills2026-lekiwi
python3 -m pip install -e .
```

If you want to use SmolVLA later, install the LeRobot extras in your LeRobot environment:

```bash
cd ../lerobot
python3 -m pip install -e ".[smolvla]"
```

## Beginner quick start

1. Start the beginner setup UI:

```bash
skills2026 ui
```

2. In the UI:
- detect front and wrist cameras
- assign leader arm and robot serial ports
- save a profile
- run the readiness check

3. Capture live setup values once the robot is powered:

```bash
skills2026 setup
```

4. Start with teleop:

```bash
skills2026 teleop
```

## Common commands

```bash
skills2026 ui
skills2026 setup --skip-live
skills2026 doctor
skills2026 teleop
skills2026 record insert_fuse
skills2026 replay default_fuse_insert 0
skills2026 competition ecu --primitive insert_fuse --target-color green
skills2026 competition ecu --backend smolvla --primitive insert_fuse --policy-path YOUR_USER/YOUR_LEKIWI_SMOLVLA
```

## Runtime model

- `dev_remote`: robot host on the robot, operator tools on a laptop
- `competition_local`: perception and control run locally on the robot
- front camera runs continuously for scene understanding
- wrist camera is used during the precision phase to protect Pi 5 4 GB headroom

## Notes

- `skills2026 ui` opens a browser-based setup app for hardware discovery, profile editing, and readiness checks.
- `skills2026 setup --skip-live` works before the robot is powered; rerun `skills2026 setup` later to capture service poses and camera homographies.
- The runtime is designed to work on a Pi 5 4 GB by running the front camera continuously and only using the wrist camera during precision phases.
- SmolVLA is supported as a second backend, but it should use a fine-tuned LeKiwi checkpoint. The package intentionally treats `lerobot/smolvla_base` as bring-up only unless you pass `--allow-base-model`.
- Transformer primitives are scaffolded but intentionally conservative. Fuse and board workflows are the main first-class tasks.
