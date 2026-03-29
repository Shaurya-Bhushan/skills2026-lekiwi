from __future__ import annotations

from dataclasses import dataclass, field

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.constants import ARM_JOINT_KEYS, BASE_VEL_KEYS
from skills2026.profile import Skills2026Profile

ensure_lerobot_on_path()

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: E402
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig  # noqa: E402


@dataclass
class LeKiwiIO:
    profile: Skills2026Profile
    last_observation: dict | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        camera_configs = {
            role: OpenCVCameraConfig(
                index_or_path=camera.source_id,
                width=camera.width,
                height=camera.height,
                fps=camera.fps,
            )
            for role, camera in self.profile.cameras.items()
            if camera.enabled
        }
        config = LeKiwiClientConfig(
            remote_ip=self.profile.host.remote_ip,
            port_zmq_cmd=self.profile.host.cmd_port,
            port_zmq_observations=self.profile.host.observation_port,
            connect_timeout_s=self.profile.host.connect_timeout_s,
            id=self.profile.robot_id,
            cameras=camera_configs,
        )
        self.robot = LeKiwiClient(config)

    def connect(self) -> None:
        self.robot.connect()

    def disconnect(self) -> None:
        if self.robot.is_connected:
            self.robot.disconnect()

    def get_observation(self) -> dict:
        observation = self.robot.get_observation()
        self.last_observation = observation
        return observation

    def arm_pose_from_observation(self, observation: dict) -> dict[str, float]:
        return {joint: float(observation.get(joint, 0.0)) for joint in ARM_JOINT_KEYS}

    def zero_action(self, observation: dict | None = None) -> dict[str, float]:
        observation = observation or self.last_observation
        arm_state = {joint: 0.0 for joint in ARM_JOINT_KEYS}
        if observation is not None:
            arm_state = self.arm_pose_from_observation(observation)
        return {
            **arm_state,
            "x.vel": 0.0,
            "y.vel": 0.0,
            "theta.vel": 0.0,
        }

    def merge_action(
        self,
        arm_pose: dict[str, float],
        base_vel: dict[str, float] | None = None,
    ) -> dict[str, float]:
        merged = {joint: float(arm_pose.get(joint, 0.0)) for joint in ARM_JOINT_KEYS}
        base_values = base_vel or {}
        for key in BASE_VEL_KEYS:
            merged[key] = float(base_values.get(key, 0.0))
        return merged

    def send_action(self, action: dict[str, float]) -> dict:
        return self.robot.send_action(action)

    def stop_base(self, observation: dict | None = None) -> None:
        self.send_action(self.zero_action(observation))
