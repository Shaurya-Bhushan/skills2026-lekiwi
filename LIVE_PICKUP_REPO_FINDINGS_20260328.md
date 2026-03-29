## Live Repo Findings

Checked against upstream `main` at `7b8e7bda4b673c72a736ca1d9f466d4cda5f2037` and the Raspberry Pi checkout that was still running `7a03f9643e6d2c1babb8aaa734d524675241e43e`.

### Confirmed facts

- Latest upstream currently exposes `45` unittest-style test cases across `10` files.
- In the Pi `lerobot` environment, `PYTHONPATH=src ~/miniforge3/envs/lerobot/bin/python -m unittest discover -s tests -p 'test_*.py'` passes on upstream `main`.
- Green tests did **not** translate into a verified live pickup on the robot.

### Confirmed repo issues

1. Pickup action completion could be blocked by stale saved gripper values.
   - The controller commands `spec.gripper_value` during `GRASP_OR_INSERT`.
   - Before this branch, `_pose_reached(current_pose, action_pose, tol=1.5)` still compared against the raw saved `arm_gripper.pos` from the service pose.
   - If the captured service pose saved the gripper while open, the FSM could wait forever for an impossible pose even though the commanded grasp was otherwise correct.
   - This branch fixes that by ignoring saved `arm_gripper.pos` when checking pickup action-pose completion for primitives that explicitly command a gripper value.

2. Pickup validation only checked for missing poses, not contradictory poses.
   - Upstream `pickup_validation` refused empty service poses, but it would still run with action poses whose saved `arm_gripper.pos` directly contradicted the primitive spec.
   - That lets a live session fail for configuration reasons while the tool reports only trial failures.
   - This branch adds a preflight warning/error path for that class of inconsistent pickup pose.

3. The current repo does not encode the wooden-block sandbox workflow that was being used on the Pi.
   - Latest `main` has no `pick_block` primitive, no sandbox command, and no block-specific workflow.
   - That means the exact live wooden-block path cannot currently be regression-tested against upstream `main`.
   - I did not reintroduce that workflow in this branch because upstream has clearly shifted toward generic pickup validation and Ontario primitives.

4. Live success still depends on physical setup checks that the test suite does not cover.
   - Front camera framing on the Pi did not reliably show the source area during the live block attempts.
   - Captured service poses on the Pi were stale relative to the actual robot configuration.
   - The repo has better pickup logic now, but it still lacks a built-in live framing sanity check before pickup validation begins.

### What this branch changes

- Fixes the gripper-pose gating bug in pickup action completion.
- Adds pickup-validation preflight warnings for action poses that save obviously inconsistent gripper values.
- Adds regression tests for both behaviors.

### What still needs attention upstream

- Add a live camera-framing preflight step before running pickup validation.
- Decide whether the removed sandbox/block workflow should exist in a supported form, or whether all validation should be expressed through the generic pickup suites.
- Add at least one hardware-in-the-loop validation checklist or smoke-test workflow, because current tests are still purely logic-level.
