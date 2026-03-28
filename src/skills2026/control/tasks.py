from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchTaskSpec:
    name: str
    label: str
    category: str
    description: str
    primitive_sequence: tuple[str, ...]
    target_color: str | None = None
    target_slot: str | None = None
    manual_note: str = ""
    enabled: bool = True


TASKS: dict[str, MatchTaskSpec] = {
    "clear_debris": MatchTaskSpec(
        name="clear_debris",
        label="Clear Debris",
        category="disaster_rescue",
        description="Pick debris pieces and move them to the debris zone.",
        primitive_sequence=("pick_debris", "drop_debris"),
        target_slot="debris_zone",
        manual_note="Park the base so the arm can reach the debris pile and debris zone cleanly.",
    ),
    "repair_fuse_circuit": MatchTaskSpec(
        name="repair_fuse_circuit",
        label="Repair Fuse Circuit",
        category="ecu",
        description="Deliver and install the correct fuse into the ECU.",
        primitive_sequence=("pick_fuse", "insert_fuse"),
        target_color="green",
        target_slot="ecu_zone",
        manual_note="Park the base at the ECU service pose before starting fuse work.",
    ),
    "repair_board_circuit": MatchTaskSpec(
        name="repair_board_circuit",
        label="Repair Board Circuit",
        category="ecu",
        description="Deliver and insert the correct board into the ECU.",
        primitive_sequence=("pick_board", "insert_board"),
        target_slot="center",
        manual_note="Keep the ECU fully visible to the front camera before starting board work.",
    ),
    "repair_transformer": MatchTaskSpec(
        name="repair_transformer",
        label="Repair Transformer",
        category="ecu",
        description="Unlock the transformer bolts and replace the transformer.",
        primitive_sequence=("unlock_transformer_bolts", "replace_transformer"),
        target_slot="left",
        manual_note="Only start transformer work after you have a stable ECU view and enough arm clearance.",
    ),
    "deliver_supply_item": MatchTaskSpec(
        name="deliver_supply_item",
        label="Deliver Supply Item",
        category="safe_room",
        description="Move a supply item into the safe room.",
        primitive_sequence=("pick_supply_item", "deliver_supply_item"),
        target_slot="safe_room",
        manual_note="Park the base so the arm can reach the supply item and safe-room placement area.",
    ),
    "orient_supply_item": MatchTaskSpec(
        name="orient_supply_item",
        label="Orient Supply Item",
        category="safe_room",
        description="Rotate or settle the supply item into a correct final orientation.",
        primitive_sequence=("orient_supply_item",),
        target_slot="safe_room",
    ),
    "install_ecu_fan": MatchTaskSpec(
        name="install_ecu_fan",
        label="Install ECU Fan",
        category="safe_room",
        description="Place the ECU fan in the correct mounting area.",
        primitive_sequence=("pick_ecu_fan", "place_ecu_fan"),
        target_slot="fan_mount",
    ),
    "stand_workers": MatchTaskSpec(
        name="stand_workers",
        label="Stand Workers",
        category="safe_room",
        description="Place worker figures upright in the safe room.",
        primitive_sequence=("pick_worker", "place_worker_upright"),
        target_slot="workers_zone",
    ),
    "deliver_steve": MatchTaskSpec(
        name="deliver_steve",
        label="Deliver Steve To Lobby",
        category="evacuation",
        description="Carry Steve and place him in the lobby.",
        primitive_sequence=("pick_steve", "deliver_steve_to_lobby"),
        target_slot="lobby",
        manual_note="Park the base so the arm can reach Steve safely before carrying him to the lobby.",
    ),
    "park_autonomous_bot": MatchTaskSpec(
        name="park_autonomous_bot",
        label="Park Autonomous Bot",
        category="evacuation",
        description="Place the autonomous bot into the target zone.",
        primitive_sequence=("pick_autonomous_bot", "park_autonomous_bot"),
        target_slot="autonomous_bot_zone",
        manual_note="Line up the base so the bot zone is visible and the drop is collision-free.",
    ),
}


MISSION_PRESETS: dict[str, tuple[str, ...]] = {
    "ecu_only": (
        "repair_fuse_circuit",
        "repair_board_circuit",
        "repair_transformer",
    ),
    "rescue_support": (
        "clear_debris",
        "deliver_supply_item",
        "orient_supply_item",
        "install_ecu_fan",
        "stand_workers",
        "deliver_steve",
        "park_autonomous_bot",
    ),
    "full_match": (
        "clear_debris",
        "repair_fuse_circuit",
        "repair_board_circuit",
        "repair_transformer",
        "deliver_supply_item",
        "orient_supply_item",
        "install_ecu_fan",
        "stand_workers",
        "deliver_steve",
        "park_autonomous_bot",
    ),
}
