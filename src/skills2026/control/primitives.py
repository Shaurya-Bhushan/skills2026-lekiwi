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
    "pick_fuse": PrimitiveSpec(
        name="pick_fuse",
        coarse_pose="tray_hover",
        action_pose="tray_grasp",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=20.0,
    ),
    "insert_fuse": PrimitiveSpec(
        name="insert_fuse",
        coarse_pose="fuse_insert_hover",
        action_pose="fuse_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
    ),
    "pick_board": PrimitiveSpec(
        name="pick_board",
        coarse_pose="tray_hover",
        action_pose="tray_grasp",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=25.0,
    ),
    "insert_board": PrimitiveSpec(
        name="insert_board",
        coarse_pose="board_insert_hover",
        action_pose="board_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
    ),
    "unlock_transformer_bolts": PrimitiveSpec(
        name="unlock_transformer_bolts",
        coarse_pose="transformer_bolt_hover",
        action_pose="transformer_bolt_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        enabled=False,
    ),
    "replace_transformer": PrimitiveSpec(
        name="replace_transformer",
        coarse_pose="transformer_insert_hover",
        action_pose="transformer_insert_pose",
        retract_pose="safe_retract",
        camera_role="wrist",
        gripper_value=80.0,
        enabled=False,
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
    alignment_hits: int = 0

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
                self.fsm.transition(PrimitiveState.APPROACH_COARSE)
                return ControlDecision(
                    action=self._move_towards_pose(current_pose, coarse_pose, self.profile.servo["front"].max_step),
                    message="coarse target acquired",
                )
            self.fsm.transition(PrimitiveState.DETECT_GLOBAL)
            return ControlDecision(action=current_pose, message="waiting for front-camera target")

        if state == PrimitiveState.APPROACH_COARSE:
            if self._pose_reached(current_pose, coarse_pose):
                self.fsm.transition(PrimitiveState.SWITCH_TO_WRIST_PRECISION)
                return ControlDecision(action=current_pose, message="coarse pose reached")
            self.fsm.transition(PrimitiveState.APPROACH_COARSE)
            return ControlDecision(
                action=self._move_towards_pose(current_pose, coarse_pose, self.profile.servo["front"].max_step),
                message="moving to coarse pose",
            )

        if state == PrimitiveState.SWITCH_TO_WRIST_PRECISION:
            if not wrist_allowed:
                self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
                return ControlDecision(action=current_pose, message="wrist disabled, continuing front-only")
            if detections.fine_target and detections.fine_target.found:
                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(action=current_pose, message="wrist target acquired", use_wrist=True)
            if self.fsm.cycles_in_state > 10:
                self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
                return ControlDecision(action=current_pose, message="wrist target timeout", use_wrist=True)
            self.fsm.transition(PrimitiveState.SWITCH_TO_WRIST_PRECISION)
            return ControlDecision(action=current_pose, message="waiting for wrist target", use_wrist=True)

        if state == PrimitiveState.ALIGN_FINE:
            fine = detections.fine_target
            if fine and fine.found and fine.error_px is not None:
                tol = self.profile.servo["wrist"].tolerance_px
                if abs(fine.error_px[0]) <= tol and abs(fine.error_px[1]) <= tol:
                    self.alignment_hits += 1
                else:
                    self.alignment_hits = 0

                if self.alignment_hits >= 3:
                    self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
                    return ControlDecision(action=current_pose, message="fine alignment locked", use_wrist=True)

                self.fsm.transition(PrimitiveState.ALIGN_FINE)
                return ControlDecision(
                    action=self._apply_servo(current_pose, fine, self.profile.servo["wrist"]),
                    message="fine-aligning with wrist camera",
                    use_wrist=True,
                )

            self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
            return ControlDecision(action=current_pose, message="lost wrist target", use_wrist=True)

        if state == PrimitiveState.GRASP_OR_INSERT:
            command = self._move_towards_pose(current_pose, action_pose, self.profile.servo["wrist"].max_step)
            if self.spec.gripper_value is not None:
                command["arm_gripper.pos"] = self.spec.gripper_value
            if self._pose_reached(current_pose, action_pose, tol=1.5):
                self.fsm.transition(PrimitiveState.VERIFY)
                return ControlDecision(action=command, message="action pose reached", use_wrist=True)
            self.fsm.transition(PrimitiveState.GRASP_OR_INSERT)
            return ControlDecision(action=command, message="executing grasp/insert", use_wrist=True)

        if state == PrimitiveState.VERIFY:
            verified = detections.verified
            if detections.fine_target and detections.fine_target.metadata.get("verified") is True:
                verified = True
            if verified or self.spec.success_mode != "verify":
                self.fsm.pending_after_retract = PrimitiveState.DONE
                self.fsm.transition(PrimitiveState.RETRACT)
                return ControlDecision(action=current_pose, message="verification passed", use_wrist=True)
            self.fsm.transition(PrimitiveState.RETRY_OR_ABORT)
            return ControlDecision(action=current_pose, message="verification failed", use_wrist=True)

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

