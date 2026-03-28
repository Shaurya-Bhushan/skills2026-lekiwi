from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PrimitiveState(str, Enum):
    DETECT_GLOBAL = "detect_global"
    APPROACH_COARSE = "approach_coarse"
    SWITCH_TO_WRIST_PRECISION = "switch_to_wrist_precision"
    ALIGN_FINE = "align_fine"
    GRASP_OR_INSERT = "grasp_or_insert"
    VERIFY = "verify"
    RETRACT = "retract"
    RETRY_OR_ABORT = "retry_or_abort"
    DONE = "done"
    FAILED = "failed"


@dataclass
class FSMStatus:
    state: PrimitiveState = PrimitiveState.DETECT_GLOBAL
    retries: int = 0
    cycles_in_state: int = 0
    pending_after_retract: PrimitiveState = PrimitiveState.DONE

    def transition(self, next_state: PrimitiveState) -> None:
        if next_state == self.state:
            self.cycles_in_state += 1
        else:
            self.state = next_state
            self.cycles_in_state = 0

