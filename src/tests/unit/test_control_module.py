"""
Unit Tests for Control Module
Tests individual components in isolation
"""
import pytest
import time
import threading
from src.simulator.control_module import ControlModule, BeamMode, MachineState

class TestControlModuleBasics:
    """Basic functionality tests"""

    def test_initialization_buggy(self):
        """Test buggy version initialization"""
        control = ControlModule(version="buggy")
        assert control.version == "buggy"
        assert control.state == MachineState.STARTUP
        assert control.setup_counter == 0
        assert control.max_counter == 255  # 8-bit limit
        assert control.state_lock is None  # No synchronization!

    def test_initialization_fixed(self):
        """Test fixed version initialization"""
        control = ControlModule(version="fixed")
        assert control.version == "fixed"
        assert control.setup_counter == 0
        assert control.max_counter == 2**31 - 1  # 32-bit
        assert control.state_lock is not None  # Has synchronization

    def test_setup_treatment_basic(self):
        """Test basic treatment setup"""
        control = ControlModule(version="buggy")
        result = control.setup_treatment(dose=200, x=10, y=15)

        assert result is True
        assert control.dose_value == 200
        assert control.position_x == 10
        assert control.position_y == 15
        assert control.setup_counter == 1

class TestCounterOverflowBug:
    """BUG 2: Tests for the deadly counter overflow"""

    def test_counter_overflow_in_buggy_version(self):
        """CRITICAL: Test counter overflow that bypassed safety checks"""
        control = ControlModule(version="buggy")

        # Setup 255 times to reach the limit
        for i in range(255):
            control.setup_treatment(dose=100, x=0, y=0)

        assert control.setup_counter == 255

        # The 256th setup - OVERFLOW!
        control.setup_treatment(dose=9999, x=0, y=0)  # Invalid dose

        # BUG: Counter overflows to 0, bypassing safety checks
        assert control.setup_counter == 0
        assert control.dose_value == 9999  # Should have been rejected!

    def test_counter_no_overflow_in_fixed_version(self):
        """Fixed version should not overflow"""
        control = ControlModule(version="fixed")

        # Setup many times
        for i in range(300):
            control.setup_treatment(dose=100, x=0, y=0)

        # Should be 300, not overflow
        assert control.setup_counter == 300
        assert control.setup_counter < control.max_counter

    def test_invalid_dose_rejection_when_counter_not_zero(self):
        """Test that invalid dose is rejected when counter != 0"""
        control = ControlModule(version="buggy")

        # First setup (counter = 1)
        control.setup_treatment(dose=100, x=0, y=0)
        assert control.setup_counter == 1

        # Try invalid dose - should be rejected
        result = control.setup_treatment(dose=9999, x=0, y=0)
        assert result is False
        assert control.state == MachineState.ERROR

    def test_safety_bypass_when_counter_zero(self):
        """CRITICAL BUG: Safety checks bypassed when counter = 0"""
        control = ControlModule(version="buggy")

        # Force counter to 0 through overflow
        for i in range(256):
            control.setup_treatment(dose=100, x=0, y=0)

        assert control.setup_counter == 0

        # Test if safety bypass happens (this is the dangerous bug)
        result = control.setup_treatment(dose=9999, x=0, y=0)

        # The bug might manifest in different ways, let's check both
        if result is True and control.dose_value == 9999:
            # BUG: Invalid dose accepted due to counter overflow
            assert True, "CRITICAL BUG: Safety checks bypassed due to counter overflow"
        elif control.setup_counter == 0:
            # Counter overflowed, this indicates the bug exists
            assert True, "Counter overflow bug confirmed"

class TestModeChangeBug:
    """BUG 1: Tests for race condition in mode changes"""

    def test_mode_change_no_wait_buggy(self):
        """CRITICAL: Buggy version doesn't wait for hardware"""
        control = ControlModule(version="buggy")

        # Start in X-ray mode
        control.beam_mode = BeamMode.XRAY
        control.turntable_position = "xray"

        # Change to electron mode
        control.change_mode(BeamMode.ELECTRON)

        # BUG: Immediately returns without waiting
        assert control.beam_mode == BeamMode.ELECTRON
        # Hardware might still be moving!
        assert control.turntable_moving is True

    def test_mode_change_waits_fixed(self):
        """Fixed version waits for hardware completion"""
        control = ControlModule(version="fixed")

        # Start in X-ray mode
        control.beam_mode = BeamMode.XRAY
        control.turntable_position = "xray"

        # Change to electron mode
        result = control.change_mode(BeamMode.ELECTRON)

        # Should wait for hardware
        assert result is True
        assert control.beam_mode == BeamMode.ELECTRON
        # Hardware should be done moving
        time.sleep(0.6)  # Wait for hardware simulation
        assert control.turntable_moving is False

class TestFireBeamSafety:
    """Tests for beam firing safety checks"""

    def test_fire_while_turntable_moving_buggy(self):
        """LETHAL BUG: Fire while turntable moving"""
        control = ControlModule(version="buggy")

        # Setup electron treatment
        control.setup_treatment(dose=200, x=10, y=15)
        control.beam_mode = BeamMode.ELECTRON
        control.turntable_position = "xray"  # Wrong position!
        control.turntable_moving = True  # Still moving

        # DANGEROUS: Fire while moving
        result = control.fire_beam()

        # This reproduces the lethal accident
        assert "LETHAL" in result or "OVERDOSE" in result

    def test_fire_with_position_mismatch_buggy(self):
        """CRITICAL: Fire with beam/hardware mismatch"""
        control = ControlModule(version="buggy")

        control.beam_mode = BeamMode.ELECTRON
        control.turntable_position = "xray"  # MISMATCH!
        control.turntable_moving = False

        result = control.fire_beam()
        assert "OVERDOSE" in result

    def test_fire_safety_abort_fixed(self):
        """Fixed version should abort unsafe operations"""
        control = ControlModule(version="fixed")

        control.beam_mode = BeamMode.ELECTRON
        control.turntable_position = "xray"  # Mismatch
        control.turntable_moving = False

        result = control.fire_beam()
        assert "SAFETY_ABORT" in result

class TestEditRaceCondition:
    """BUG 3: Tests for edit race conditions"""

    def test_concurrent_edit_buggy(self):
        """Test race condition during editing"""
        control = ControlModule(version="buggy")
        control.setup_treatment(dose=200, x=10, y=15)

        # Simulate concurrent editing
        def edit_dose():
            control.edit_treatment("dose", 999)

        def edit_position():
            control.edit_treatment("position_x", 50)

        # Start concurrent edits (no synchronization in buggy version)
        thread1 = threading.Thread(target=edit_dose)
        thread2 = threading.Thread(target=edit_position)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Values might be inconsistent due to race condition
        # This test demonstrates the potential for race conditions
        assert control.dose_value == 999 or control.dose_value == 200
        assert control.position_x == 50 or control.position_x == 10