import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.commands.shared import maybe_start_local_host


class _FakeProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True


class SharedTests(unittest.TestCase):
    @patch("skills2026.commands.shared.tcp_port_open", side_effect=[(True, "reachable"), (True, "reachable")])
    @patch("skills2026.commands.shared.ensure_lerobot_on_path", return_value=Path("/tmp/lerobot/src"))
    @patch("skills2026.commands.shared.subprocess.Popen")
    def test_local_host_launcher_uses_profile_ports(
        self,
        mock_popen,
        _ensure_lerobot_on_path,
        _tcp_port_open,
    ):
        process = _FakeProcess()
        mock_popen.return_value = process
        profile = SimpleNamespace(
            host=SimpleNamespace(
                start_local_host=True,
                connection_time_s=30,
                connect_timeout_s=5,
                remote_ip="127.0.0.1",
                cmd_port=6123,
                observation_port=6124,
            ),
            robot_id="skills2026_lekiwi",
            robot_serial_port="/dev/ttyACM0",
        )

        returned = maybe_start_local_host(profile)

        self.assertIs(returned, process)
        cmd = mock_popen.call_args.args[0]
        self.assertIn("--host.port_zmq_cmd=6123", cmd)
        self.assertIn("--host.port_zmq_observations=6124", cmd)
        self.assertIn("--robot.port=/dev/ttyACM0", cmd)

    @patch("skills2026.commands.shared.tcp_port_open", return_value=(True, "reachable"))
    @patch("skills2026.commands.shared.ensure_lerobot_on_path", return_value=Path("/tmp/lerobot/src"))
    @patch("skills2026.commands.shared.subprocess.Popen")
    def test_local_host_launcher_raises_when_host_exits_immediately(
        self,
        mock_popen,
        _ensure_lerobot_on_path,
        _tcp_port_open,
    ):
        process = _FakeProcess(returncode=1)
        mock_popen.return_value = process
        profile = SimpleNamespace(
            host=SimpleNamespace(
                start_local_host=True,
                connection_time_s=30,
                connect_timeout_s=5,
                remote_ip="127.0.0.1",
                cmd_port=6123,
                observation_port=6124,
            ),
            robot_id="skills2026_lekiwi",
            robot_serial_port="",
        )

        with self.assertRaises(RuntimeError):
            maybe_start_local_host(profile)

        self.assertFalse(process.terminated)


if __name__ == "__main__":
    unittest.main()
