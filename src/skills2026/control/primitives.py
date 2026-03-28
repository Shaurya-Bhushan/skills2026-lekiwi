from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skills2026.constants import ARM_JOINT_KEYS
from skills2026.control.fsm import FSMStatus, PrimitiveState
from skills2026.perception.models import DetectionBundle
from skills2026.profile import ServoProfile, Skills2026Profile


@dataclass(frozen=True)
class PrimitiveSpec:
    name: str
    coarse_pose: str
    action_pose: str
    retract_pose: str
    camera_role: str
    gripper_value: float | None = None
    success_mode: str = "verify"
    enabled: bool = True


PRIMITIVES: dict[str, PrimitiveSpec] = {
    "remove_fuse": PrimitiveSpec(
        name="remove_fuse",
        coarse_pose="fuse_remove_hover",
        action_pose="fuse_remove_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=18.0,
        success_mode="pose",
    ),
    "pick_fuse": PrimitiveSpec(
        name="pick_fuse",
        coarse_pose="tray_hover",
        action_pose="tray_grasp",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=20.0,
        success_mode="pose",
    ),
    "insert_fuse": PrimitiveSpec(
        name="insert_fuse",
        coarse_pose="fuse_insert_hover",
        action_pose="fuse_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
    ),
    "remove_board": PrimitiveSpec(
        name="remove_board",
        coarse_pose="board_remove_hover",
        action_pose="board_remove_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=24.0,
        success_mode="pose",
    ),
    "pick_board": PrimitiveSpec(
        name="pick_board",
        coarse_pose="tray_hover",
        action_pose="tray_grasp",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=25.0,
        success_mode="pose",
    ),
    "insert_board": PrimitiveSpec(
        name="insert_board",
        coarse_pose="board_insert_hover",
        action_pose="board_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
    ),
    "pick_transformer": PrimitiveSpec(
        name="pick_transformer",
        coarse_pose="transformer_supply_hover",
        action_pose="transformer_supply_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=26.0,
        success_mode="pose",
    ),
    "remove_transformer": PrimitiveSpec(
        name="remove_transformer",
        coarse_pose="transformer_remove_hover",
        action_pose="transformer_remove_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=26.0,
        success_mode="pose",
    ),
    "pick_debris": PrimitiveSpec(
        name="pick_debris",
        coarse_pose="debris_hover",
        action_pose="debris_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=25.0,
        success_mode="pose",
    ),
    "drop_debris": PrimitiveSpec(
        name="drop_debris",
        coarse_pose="debris_zone_hover",
        action_pose="debris_zone_drop_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=85.0,
        success_mode="pose",
    ),
    "push_fallen_beam": PrimitiveSpec(
        name="push_fallen_beam",
        coarse_pose="beam_hover",
        action_pose="beam_push_pose",
        retract_pose="safe_retract",
        camera_role="front",
        success_mode="pose",
    ),
    "pick_supply_item": PrimitiveSpec(
        name="pick_supply_item",
        coarse_pose="supply_hover",
        action_pose="supply_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=28.0,
        success_mode="pose",
    ),
    "deliver_supply_item": PrimitiveSpec(
        name="deliver_supply_item",
        coarse_pose="safe_room_hover",
        action_pose="safe_room_place_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=82.0,
        success_mode="pose",
    ),
    "orient_supply_item": PrimitiveSpec(
        name="orient_supply_item",
        coarse_pose="safe_room_hover",
        action_pose="safe_room_orient_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=70.0,
        success_mode="pose",
    ),
    "pick_worker": PrimitiveSpec(
        name="pick_worker",
        coarse_pose="worker_hover",
        action_pose="worker_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=18.0,
        success_mode="pose",
    ),
    "place_worker_upright": PrimitiveSpec(
        name="place_worker_upright",
        coarse_pose="worker_zone_hover",
        action_pose="worker_place_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=82.0,
        success_mode="pose",
    ),
    "pick_steve": PrimitiveSpec(
        name="pick_steve",
        coarse_pose="steve_hover",
        action_pose="steve_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=22.0,
        success_mode="pose",
    ),
    "deliver_steve_to_lobby": PrimitiveSpec(
        name="deliver_steve_to_lobby",
        coarse_pose="lobby_hover",
        action_pose="lobby_place_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=85.0,
        success_mode="pose",
    ),
    "pick_ecu_fan": PrimitiveSpec(
        name="pick_ecu_fan",
        coarse_pose="fan_hover",
        action_pose="fan_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=24.0,
        success_mode="pose",
    ),
    "place_ecu_fan": PrimitiveSpec(
        name="place_ecu_fan",
        coarse_pose="fan_mount_hover",
        action_pose="fan_mount_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=84.0,
        success_mode="pose",
    ),
    "pick_autonomous_bot": PrimitiveSpec(
        name="pick_autonomous_bot",
        coarse_pose="bot_hover",
        action_pose="bot_pick_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=24.0,
        success_mode="pose",
    ),
    "park_autonomous_bot": PrimitiveSpec(
        name="park_autonomous_bot",
        coarse_pose="bot_zone_hover",
        action_pose="bot_zone_place_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=84.0,
        success_mode="pose",
    ),
    "flip_breaker_on": PrimitiveSpec(
        name="flip_breaker_on",
        coarse_pose="breaker_hover",
        action_pose="breaker_flip_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        success_mode="pose",
    ),
    "park_final_robot": PrimitiveSpec(
        name="park_final_robot",
        coarse_pose="final_zone_hover",
        action_pose="final_zone_pose",
        retract_pose="safe_retract",
        camera_role="front",
        success_mode="pose",
    ),
    "unlock_transformer_bolts": PrimitiveSpec(
        name="unlock_transformer_bolts",
        coarse_pose="transformer_bolt_hover",
        action_pose="transformer_bolt_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        success_mode="pose",
    ),
    "replace_transformer": PrimitiveSpec(
        name="replace_transformer",
        coarse_pose="transformer_insert_hover",
        action_pose="transformer_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
        success_mode="pose",
    ),
}


@dataclass
class ControlDecision:
    action: dict[str, float]
    message: str
    use_wrist: bool = False
    done: bool = False
    failed: bool = False


@dataclass
class PrimitiveController:
    spec: PrimitiveSpec
    profile: Skills2026Profile
    target_color: str | None = None
    target_slot: str | None = None
    fsm: FSMStatus = field(default_factory=FSMStatus)
    coarse_alignment_hits: int = 0
    lost_coarse_cycles: int = 0
    alignment_hits: int = 0
    wrist_settle_cycles_remaining: int = 0
    lost_wrist_cycles: int = 0
    front_target_miss_grace_cycles: int = 3
    coarse_alignment_required_hits: int = 2
    wrist_settle_cycles_after_servo: int = 2
    wrist_settle_cycles_after_action: int = 2
    wrist_target_miss_grace_cycles: int = 3
    wrist_action_step_scale: float = 0.6
    action_hold_cycles_required: int = 2
    action_hold_cycles_remaining: int = 0
    action_hold_started: bool = False

    def _pose(self, pose_name: str) -> dict[str, float]:
        return dict(self.profile.service_poses.get(pose_name, {}))

    def _move_towards_pose(
        self,
        current_pose: dict[str, float],
        target_pose: dict[str, float],
        max_step: float,
    ) -> dict[str, float]:
        command = dict(current_pose)
        for joint in ARM_JOINT_KEYS:
            if joint not in target_pose:
                continue
            current = float(current_pose.get(joint, 0.0))
            target = float(target_pose[joint])
            delta = target - current
            if abs(delta) <= max_step:
                command[joint] = target
            else:
                command[joint] = current + max_step * (1.0 if delta > 0 else -1.0)
        return command

    def _pose_reached(self, current_pose: dict[str, float], target_pose: dict[str, float], tol: float = 1.0) -> bool:
        relevant = [joint for joint in ARM_JOINT_KEYS if joint in target_pose]
        if not relevant:
            return False
        return all(abs(float(current_pose.get(joint, 0.0)) - float(target_pose[joint])) <= tol for joint in relevant)

    def _apply_servo(
        self,
        current_pose: dict[str, float],
        target,
        servo: ServoProfile,
    ) -> dict[str, float]:
        command = dict(current_pose)
        if not target.found or target.error_px is None:
            return command
        dx, dy = target.error_px
        for joint, gain in servo.x_gains.items():
            command[joint] = float(command.get(joint, 0.0)) + (dx / 100.0) * gain
        for joint, gain in servo.y_gains.items():
            command[joint] = float(command.get(joint, 0.0)) + (dy / 100.0) * gain
        return command

    def _has_meaningful_motion(
        self,
        current_pose: dict[str, float],
        commanded_pose: dict[str, float],
        tol: float = 0.05,
    ) -> bool:
        return any(abs(float(commanded_pose.get(joint, 0.0)) - float(current_pose.get(joint, 0.0))) > tol for joint in ARM_JOINT_KEYS)

    def step(
        self,
        current_pose: dict[str, float],
        detections: DetectionBundle,
        wrist_allowed: bool,
    ) -> ControlDecision:
        state = self.fsm.state
        coarse_pose = self._pose(self.spec.coarse_pose)
        action_pose = self._pose(self.spec.action_pose)
        retract_pose = self._pose(self.spec.retract_pose)

        if state == PrimitiveState.DETECT_GLOBAL:
            if detections.coarse_target and detections.coarse_target.found:
                self.coarse_alignment_hits = 0
                self.lost_coarse_cycles = 0
                self.fsm.transition(PrimitiveState.APPROACH_COARSE)
                return ControlDecision(
                    action=self._move_towards_pose(current_pose, coarse_pose, self.profile.servo["front"].max_step),
                    message="coarse target acquired",
                )
            self.fsm.transition(PrimitiveState.DETECT_GLOBAL)
            return ControlDecision(action=current_pose, message="waiting for front-camera target")

        if state == PrimitiveState.APPROACH_COARSE:
            if not self._pose_reached(current_pose, coarse_pose):
                self.fsm.transition(PrimitiveState.APPROACH_COARSE)
                return ControlDecision(
                    action=self._move_towards_pose(current_pose, coarse_pose, self.profile.servo["front"].max_step),
                    message="moving to coarse pose",
                )

            coarse = detections.coarse_target
            if coarse and coarse.found and coarse.error_px is not None:
                self.lost_coarse_cycles = 0
                tol = self.profile.servo["front"].tolerance_px
                if abs(coarse.error_px[0]) <= tol and abs(coarse.error_px[1]) <= tol:
                    self.coarse_alignment_hits += 1
                else:
                    self.coarse_alignment_hits = 0

                if self.coarse_alignment_hits >= self.coarse_alignment_required_hits:
                    self.fsm.transition(PrimitiveState.SWITCH_TO_WRIST_PRECISION)
                    return ControlDecision(action=current_pose, message="coarse alignment locked")

                self.fsm.transition(PrimitiveState.APPROACH_COARSE)
                return ControlDecision(
                    action=self._apply_servo(current_pose, coarse, self.profile.servo["front"]),
                    message="coarse-aligning with front camera",
                )

            self.lost_coarse_cycles += 1
            if self.lost_coarse_cycles <= self.front_target_miss_grace_cycles:
                self.fsm.transition(PrimitiveState.APPROACH_COARSE)
                return ControlDecision(action=current_pose, message="waiting for front target to reappear")

            self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
            return ControlDecision(action=current_pose, message="lost front target")

        if state == PrimitiveState.SWITCH_TO_WRIST_PRECISION:
            if self.spec.camera_role != "wrist" or not wrist_allowed:
                self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
                return ControlDecision(action=current_pose, message="continuing without wrist precision")
            if detections.fine_target and detections.fine_target.found:
                self.lost_wrist_cycles = 0
                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(action=current_pose, message="wrist target acquired", use_wrist=True)
            if self.fsm.cycles_in_state > 10:
                self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
                return ControlDecision(action=current_pose, message="wrist target timeout", use_wrist=True)
            self.fsm.transition(PrimitiveState.SWITCH_TO_WRIST_PRECISION)
            return ControlDecision(action=current_pose, message="waiting for wrist target", use_wrist=True)

        if state == PrimitiveState.ALIGN_FINE:
            if self.wrist_settle_cycles_remaining > 0:
                self.wrist_settle_cycles_remaining -= 1
                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(action=current_pose, message="waiting for wrist camera to settle", use_wrist=True)

            fine = detections.fine_target
            if fine and fine.found and fine.error_px is not None:
                self.lost_wrist_cycles = 0
                tol = self.profile.servo["wrist"].tolerance_px
                if abs(fine.error_px[0]) <= tol and abs(fine.error_px[1]) <= tol:
                    self.alignment_hits += 1
                else:
                    self.alignment_hits = 0

                if self.alignment_hits >= 3:
                    self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
                    return ControlDecision(action=current_pose, message="fine alignment locked", use_wrist=True)

                command = self._apply_servo(current_pose, fine, self.profile.servo["wrist"])
                if self._has_meaningful_motion(current_pose, command):
                    # Wrist-mounted cameras need a couple of quiet frames after motion before
                    # we trust that an apparent image shift means the object actually moved.
                    self.wrist_settle_cycles_remaining = self.wrist_settle_cycles_after_servo
                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(
                    action=command,
                    message="fine-aligning with wrist camera",
                    use_wrist=True,
                )

            self.lost_wrist_cycles += 1
            if self.lost_wrist_cycles <= self.wrist_target_miss_grace_cycles:
                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(action=current_pose, message="waiting for wrist target to reappear", use_wrist=True)
            self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
            return ControlDecision(action=current_pose, message="lost wrist target", use_wrist=True)

        if state == PrimitiveState.GRASP_OR_INSERT:
            motion_profile = self.profile.servo["wrist"] if self.spec.camera_role == "wrist" else self.profile.servo["front"]
            use_wrist = self.spec.camera_role == "wrist"
            max_step = motion_profile.max_step
            if use_wrist:
                max_step = max(motion_profile.max_step * self.wrist_action_step_scale, 0.4)
            command = self._move_towards_pose(current_pose, action_pose, max_step)
            if self.spec.gripper_value is not None:
                command["arm_gripper.pos"] = self.spec.gripper_value
            if self._pose_reached(current_pose, action_pose, tol=1.5):
                if self.spec.gripper_value is not None:
                    if not self.action_hold_started:
                        self.action_hold_cycles_remaining = self.action_hold_cycles_required
                        self.action_hold_started = True
                    if self.action_hold_cycles_remaining > 0:
                        self.action_hold_cycles_remaining -= 1
                        self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
                        return ControlDecision(
                            action=command,
                            message="holding action pose to secure grasp",
                            use_wrist=use_wrist,
                        )
                self.action_hold_started = False
                self.action_hold_cycles_remaining = 0
                self.lost_wrist_cycles = 0
                self.wrist_settle_cycles_remaining = self.wrist_settle_cycles_after_action if use_wrist else 0
                self.fsm.transition(PrimitiveState.VERIFY)
                return ControlDecision(action=command, message="action pose reached", use_wrist=use_wrist)
            self.action_hold_started = False
            self.action_hold_cycles_remaining = 0
            self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
            return ControlDecision(action=command, message="executing grasp/insert", use_wrist=use_wrist)

        if state == PrimitiveState.VERIFY:
            use_wrist = self.spec.camera_role == "wrist"
            if self.wrist_settle_cycles_remaining > 0:
                self.wrist_settle_cycles_remaining -= 1
                self.fsm.transition(PrimitiveState.VERIFY)
                return ControlDecision(action=current_pose, message="waiting for post-action settle", use_wrist=use_wrist)

            verified = detections.verified
            if (
                detections.fine_target
                and detections.fine_target.metadata.get("verified") is True
                and not detections.fine_target.metadata.get("stale")
            ):
                verified = True
            if verified or self.spec.success_mode != "verify":
                self.lost_wrist_cycles = 0
                self.fsm.pending_after_retract = PrimitiveState.DONE
                self.fsm.transition(PrimitiveState.RETRACT)
                return ControlDecision(action=current_pose, message="verification passed", use_wrist=use_wrist)
            if not detections.fine_target or not detections.fine_target.found:
                self.lost_wrist_cycles += 1
                if self.lost_wrist_cycles <= self.wrist_target_miss_grace_cycles:
                    self.fsm.transition(PrimitiveState.VERIFY)
                    return ControlDecision(action=current_pose, message="verification waiting for wrist target", use_wrist=use_wrist)
            self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
            return ControlDecision(action=current_pose, message="verification failed", use_wrist=use_wrist)

        if state == PrimitiveState.RETRY_OR_ABORT:
            if self.fsm.retries < 2:
                self.fsm.retries += 1
                self.fsm.pending_after_retract = PrimitiveState.DETECT_GLOBAL
                self.fsm.transition(PrimitiveState.RETRACT)
                return ControlDecision(action=current_pose, message=f"retry {self.fsm.retries} starting")
            self.fsm.transition(PrimitiveState.FAILED)
            return ControlDecision(action=current_pose, message="primitive failed after retries", failed=True)

        if state == PrimitiveState.RETRACT:
            if self._pose_reached(current_pose, retract_pose, tol=1.5):
                next_state = self.fsm.pending_after_retract
                self.fsm.transition(next_state)
                if next_state == PrimitiveState.DONE:
                    return ControlDecision(action=current_pose, message="primitive complete", done=True)
                return ControlDecision(action=current_pose, message="retracted and restarting")
            self.fsm.transition(PrimitiveState.RETRACT)
            return ControlDecision(
                action=self._move_towards_pose(current_pose, retract_pose, self.profile.servo["front"].max_step),
                message="retracting to safe pose",
            )

        if state == PrimitiveState.DONE:
            return ControlDecision(action=current_pose, message="done", done=True)

        return ControlDecision(action=current_pose, message="failed", failed=True)
