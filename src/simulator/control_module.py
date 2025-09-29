"""
Therac-25 Control Module
Manages machine state with intentional bugs for educational purposes
"""
import threading
import time
from enum import Enum
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MachineState(Enum):
    STARTUP = "startup"
    READY = "ready"
    SETUP = "setup"
    BEAM_READY = "beam_ready"
    FIRING = "firing"
    ERROR = "error"

class BeamMode(Enum):
    XRAY = "xray"
    ELECTRON = "electron"

class ControlModule:
    def __init__(self, version="buggy"):
        self.version = version
        self.state = MachineState.STARTUP
        self.beam_mode = BeamMode.XRAY
        self.dose_value = 0
        self.position_x = 0
        self.position_y = 0

        # BUG 2: 8-bit counter that will overflow (buggy version)
        if version == "buggy":
            self.setup_counter = 0  # Will overflow at 256
            self.max_counter = 255
        else:
            self.setup_counter = 0  # 32-bit in fixed version
            self.max_counter = 2**31 - 1

        # BUG 1: No proper synchronization in buggy version
        if version == "fixed":
            self.state_lock = threading.Lock()
            self.hardware_ready_event = threading.Event()
        else:
            self.state_lock = None  # No synchronization!
            self.hardware_ready_event = None

        self.turntable_position = "xray"  # Hardware position
        self.turntable_moving = False

        logger.info(f"ControlModule initialized in {version} mode")

    def change_mode(self, new_mode: BeamMode):
        """BUG 1: Race condition - doesn't wait for hardware in buggy version"""
        logger.info(f"Changing mode from {self.beam_mode} to {new_mode}")

        if self.version == "fixed" and self.state_lock:
            with self.state_lock:
                return self._change_mode_internal(new_mode)
        else:
            # BUGGY: No synchronization
            return self._change_mode_internal(new_mode)

    def _change_mode_internal(self, new_mode: BeamMode):
        old_mode = self.beam_mode
        self.beam_mode = new_mode

        # Start turntable movement
        if old_mode != new_mode:
            self.turntable_moving = True
            # Simulate hardware movement
            threading.Thread(target=self._move_turntable, args=(new_mode,)).start()

        if self.version == "fixed":
            # FIXED: Wait for hardware confirmation
            if self.hardware_ready_event:
                logger.info("Waiting for hardware to complete movement...")
                self.hardware_ready_event.wait(timeout=5.0)
                if not self.hardware_ready_event.is_set():
                    self.state = MachineState.ERROR
                    return False
        else:
            # BUGGY: Don't wait for hardware!
            logger.warning("NOT waiting for hardware - DANGEROUS!")

        return True

    def _move_turntable(self, target_mode: BeamMode):
        """Simulates hardware turntable movement"""
        # Realistic hardware delay
        time.sleep(0.5)

        self.turntable_position = "electron" if target_mode == BeamMode.ELECTRON else "xray"
        self.turntable_moving = False

        if self.version == "fixed" and self.hardware_ready_event:
            self.hardware_ready_event.set()

        logger.info(f"Turntable moved to {self.turntable_position}")

    def setup_treatment(self, dose: int, x: int, y: int):
        """BUG 2: Counter overflow bypasses safety checks"""
        logger.info(f"Setup treatment: dose={dose}, position=({x},{y})")

        # Increment setup counter
        if self.version == "buggy":
            self.setup_counter = (self.setup_counter + 1) % 256  # OVERFLOW BUG!
        else:
            self.setup_counter += 1

        logger.info(f"Setup counter: {self.setup_counter}")

        # BUG 2: Safety check bypassed when counter overflows to 0
        if self.setup_counter == 0 and self.version == "buggy":
            logger.critical("CRITICAL: Counter overflow - safety checks BYPASSED!")
            # In real Therac-25, this allowed invalid configurations

        self.dose_value = dose
        self.position_x = x
        self.position_y = y
        self.state = MachineState.SETUP

        # Basic validation (bypassed when counter = 0 in buggy version)
        if self.setup_counter != 0 or self.version == "fixed":
            if dose <= 0 or dose > 1000:
                self.state = MachineState.ERROR
                return False

        # After successful setup, machine should be ready to fire
        self.state = MachineState.READY
        return True

    def edit_treatment(self, field: str, value: Any):
        """BUG 3: Edit race condition - partial state updates"""
        logger.info(f"Editing {field} to {value}")

        if self.version == "fixed" and self.state_lock:
            with self.state_lock:
                return self._edit_internal(field, value)
        else:
            # BUGGY: No synchronization during edit
            return self._edit_internal(field, value)

    def _edit_internal(self, field: str, value: Any):
        # BUG 3: Simulate cursor editing during state transition
        if field == "dose":
            # Simulate keystroke delay
            time.sleep(0.1)
            self.dose_value = value
        elif field == "position_x":
            time.sleep(0.1)
            self.position_x = value
        elif field == "position_y":
            time.sleep(0.1)
            self.position_y = value

        return True

    def fire_beam(self):
        """Fire the radiation beam - DANGEROUS if bugs are present"""
        logger.info("FIRING BEAM...")

        # Check if turntable is still moving (DANGEROUS!)
        if self.turntable_moving:
            if self.version == "buggy":
                logger.critical("ACCIDENT: Firing while turntable moving!")
                logger.critical(f"Beam mode: {self.beam_mode}, Hardware position: {self.turntable_position}")
                if self.beam_mode == BeamMode.ELECTRON and self.turntable_position == "xray":
                    logger.critical("LETHAL: High-power electron beam without scattering target!")
                    return "LETHAL_OVERDOSE"
            else:
                logger.error("Safety: Cannot fire while turntable moving")
                return "SAFETY_ABORT"

        # Check mode/hardware consistency
        expected_pos = "electron" if self.beam_mode == BeamMode.ELECTRON else "xray"
        if self.turntable_position != expected_pos:
            if self.version == "buggy":
                logger.critical("ACCIDENT: Beam/hardware mismatch!")
                return "OVERDOSE"
            else:
                logger.error("Safety: Beam/hardware position mismatch")
                return "SAFETY_ABORT"

        self.state = MachineState.FIRING

        # Simulate beam firing time
        import time
        time.sleep(0.5)

        # Return to ready state after firing
        self.state = MachineState.READY

        logger.info(f"Beam fired safely: {self.beam_mode} mode, dose {self.dose_value}")
        return "SUCCESS"

    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "state": self.state.value,
            "beam_mode": self.beam_mode.value,
            "dose": self.dose_value,
            "position": (self.position_x, self.position_y),
            "setup_counter": self.setup_counter,
            "turntable_position": self.turntable_position,
            "turntable_moving": self.turntable_moving,
            "version": self.version
        }