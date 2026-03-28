from __future__ import annotations

ARM_JOINT_KEYS = (
    "arm_shoulder_pan.pos",
    "arm_shoulder_lift.pos",
    "arm_elbow_flex.pos",
    "arm_wrist_flex.pos",
    "arm_wrist_roll.pos",
    "arm_gripper.pos",
)

BASE_VEL_KEYS = (
    "x.vel",
    "y.vel",
    "theta.vel",
)

FUSE_SLOT_CENTERS = {
    "orange": (0.18, 0.16),
    "green": (0.50, 0.16),
    "blue": (0.82, 0.16),
}

BOARD_SLOT_CENTERS = {
    "left": (0.20, 0.78),
    "center": (0.50, 0.78),
    "right": (0.80, 0.78),
}

TRANSFORMER_SLOT_CENTERS = {
    "left": (0.34, 0.45),
    "right": (0.66, 0.45),
}

DEFAULT_CANONICAL_SIZE = (800, 600)
DEFAULT_FRONT_FPS = 15
DEFAULT_WRIST_FPS = 12
DEFAULT_LOOP_HZ = 10.0

