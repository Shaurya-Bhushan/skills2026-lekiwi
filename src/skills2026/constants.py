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

MISSION_ZONE_CENTERS = {
    "debris_zone": (0.16, 0.78),
    "ecu_zone": (0.50, 0.24),
    "safe_room": (0.82, 0.30),
    "workers_zone": (0.56, 0.58),
    "lobby": (0.82, 0.78),
    "fan_mount": (0.62, 0.22),
    "autonomous_bot_zone": (0.22, 0.54),
}

PRIMITIVE_DEFAULT_TARGETS = {
    "pick_debris": "debris_zone",
    "drop_debris": "debris_zone",
    "pick_supply_item": "safe_room",
    "deliver_supply_item": "safe_room",
    "orient_supply_item": "safe_room",
    "pick_worker": "workers_zone",
    "place_worker_upright": "workers_zone",
    "pick_steve": "lobby",
    "deliver_steve_to_lobby": "lobby",
    "pick_ecu_fan": "fan_mount",
    "place_ecu_fan": "fan_mount",
    "pick_autonomous_bot": "autonomous_bot_zone",
    "park_autonomous_bot": "autonomous_bot_zone",
}

DEFAULT_CANONICAL_SIZE = (800, 600)
DEFAULT_FRONT_FPS = 15
DEFAULT_WRIST_FPS = 12
DEFAULT_LOOP_HZ = 10.0
