from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrimitiveStep:
    primitive_name: str
    target_color: str | None = None
    target_slot: str | None = None


@dataclass(frozen=True)
class MatchTaskSpec:
    name: str
    label: str
    category: str
    description: str
    primitive_sequence: tuple[PrimitiveStep, ...]
    manual_note: str = ""
    enabled: bool = True


TASKS: dict[str, MatchTaskSpec] = {
    "clear_debris": MatchTaskSpec(
        name="clear_debris",
        label="Clear Debris",
        category="disaster_rescue",
        description="Pick debris pieces and move them to the debris zone.",
        primitive_sequence=(
            PrimitiveStep("pick_debris"),
            PrimitiveStep("drop_debris", target_slot="debris_zone"),
        ),
        manual_note="Park the base so the arm can reach the debris pile and debris zone cleanly.",
    ),
    "move_fallen_beams": MatchTaskSpec(
        name="move_fallen_beams",
        label="Move Fallen Beams",
        category="access",
        description="Push fallen beams far enough to open a path.",
        primitive_sequence=(PrimitiveStep("push_fallen_beam", target_slot="beam_clear_path"),),
        manual_note="Park the base so the arm can push the beam sideways without trapping itself.",
    ),
    "repair_fuse_circuit": MatchTaskSpec(
        name="repair_fuse_circuit",
        label="Repair Fuse Circuit",
        category="ecu",
        description="Remove the bad fuse, discard it, then install the correct replacement fuse into the ECU.",
        primitive_sequence=(
            PrimitiveStep("remove_fuse", target_color="black", target_slot="green"),
            PrimitiveStep("drop_debris", target_slot="debris_zone"),
            PrimitiveStep("pick_fuse", target_color="green", target_slot="fuse_supply"),
            PrimitiveStep("insert_fuse", target_color="green", target_slot="green"),
        ),
        manual_note="Park the base at the ECU service pose before starting fuse work.",
    ),
    "repair_board_circuit": MatchTaskSpec(
        name="repair_board_circuit",
        label="Repair Board Circuit",
        category="ecu",
        description="Remove the broken board, discard it, then insert the replacement board into the ECU.",
        primitive_sequence=(
            PrimitiveStep("remove_board", target_slot="center"),
            PrimitiveStep("drop_debris", target_slot="debris_zone"),
            PrimitiveStep("pick_board", target_slot="board_supply"),
            PrimitiveStep("insert_board", target_slot="center"),
        ),
        manual_note="Keep the ECU fully visible to the front camera before starting board work.",
    ),
    "repair_transformer": MatchTaskSpec(
        name="repair_transformer",
        label="Repair Transformer",
        category="ecu",
        description="Unlock the transformer bolts, remove the broken transformer, discard it, then place the replacement transformer.",
        primitive_sequence=(
            PrimitiveStep("unlock_transformer_bolts", target_slot="left"),
            PrimitiveStep("remove_transformer", target_slot="left"),
            PrimitiveStep("drop_debris", target_slot="debris_zone"),
            PrimitiveStep("pick_transformer", target_slot="transformer_supply"),
            PrimitiveStep("replace_transformer", target_slot="left"),
        ),
        manual_note="Only start transformer work after you have a stable ECU view and enough arm clearance.",
    ),
    "deliver_supply_item": MatchTaskSpec(
        name="deliver_supply_item",
        label="Deliver Supply Item",
        category="safe_room",
        description="Move a supply item into the safe room.",
        primitive_sequence=(
            PrimitiveStep("pick_supply_item", target_slot="supply_source"),
            PrimitiveStep("deliver_supply_item", target_slot="safe_room"),
        ),
        manual_note="Park the base so the arm can reach the supply item and safe-room placement area.",
    ),
    "orient_supply_item": MatchTaskSpec(
        name="orient_supply_item",
        label="Orient Supply Item",
        category="safe_room",
        description="Rotate or settle the supply item into a correct final orientation.",
        primitive_sequence=(PrimitiveStep("orient_supply_item", target_slot="safe_room"),),
    ),
    "install_ecu_fan": MatchTaskSpec(
        name="install_ecu_fan",
        label="Install ECU Fan",
        category="safe_room",
        description="Place the ECU fan in the correct mounting area.",
        primitive_sequence=(
            PrimitiveStep("pick_ecu_fan", target_slot="supply_source"),
            PrimitiveStep("place_ecu_fan", target_slot="fan_mount"),
        ),
    ),
    "protect_workers": MatchTaskSpec(
        name="protect_workers",
        label="Protect Workers",
        category="safe_room",
        description="Check that workers are still standing before finishing the run.",
        primitive_sequence=(),
        manual_note="Confirm both workers are still standing. If needed, re-park before continuing.",
    ),
    "deliver_steve": MatchTaskSpec(
        name="deliver_steve",
        label="Deliver Steve To Lobby",
        category="evacuation",
        description="Carry Steve and place him in the lobby.",
        primitive_sequence=(
            PrimitiveStep("pick_steve", target_slot="steve_source"),
            PrimitiveStep("deliver_steve_to_lobby", target_slot="lobby"),
        ),
        manual_note="Park the base so the arm can reach Steve safely before carrying him to the lobby.",
    ),
    "flip_breaker": MatchTaskSpec(
        name="flip_breaker",
        label="Flip Breaker",
        category="finish",
        description="Flip the breaker ON only after ECU work is really complete.",
        primitive_sequence=(PrimitiveStep("flip_breaker_on", target_slot="breaker"),),
        manual_note="This is a finishing step. Make sure you are ready before continuing.",
    ),
    "final_position": MatchTaskSpec(
        name="final_position",
        label="Final Position",
        category="finish",
        description="Finish with the autonomous robot in the Autonomous Zone.",
        primitive_sequence=(PrimitiveStep("park_final_robot", target_slot="final_robot_zone"),),
        manual_note="If another robot handles final parking, use this step as a checklist confirmation.",
    ),
}


MISSION_PRESETS: dict[str, tuple[str, ...]] = {
    "ecu_steve_priority": (
        "repair_fuse_circuit",
        "repair_board_circuit",
        "repair_transformer",
        "deliver_steve",
        "flip_breaker",
    ),
    "ecu_only": (
        "repair_fuse_circuit",
        "repair_board_circuit",
        "repair_transformer",
    ),
    "rescue_support": (
        "move_fallen_beams",
        "clear_debris",
        "deliver_supply_item",
        "orient_supply_item",
        "install_ecu_fan",
        "protect_workers",
        "deliver_steve",
        "flip_breaker",
        "final_position",
    ),
    "full_match": (
        "move_fallen_beams",
        "clear_debris",
        "deliver_supply_item",
        "orient_supply_item",
        "repair_fuse_circuit",
        "repair_board_circuit",
        "repair_transformer",
        "install_ecu_fan",
        "protect_workers",
        "deliver_steve",
        "flip_breaker",
        "final_position",
    ),
}
