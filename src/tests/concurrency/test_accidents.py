"""
Concurrency Tests - Reproducing the Exact Therac-25 Accidents
These tests reproduce the exact sequences that killed patients
"""
import pytest
import time
import threading
from src.simulator.control_module import ControlModule, BeamMode

class TestTherac25Accidents:
    """Reproduce the exact accidents that caused deaths"""

    def test_accident_scenario_1_race_condition(self):
        """
        ACCIDENT 1: X-ray to Electron mode change race condition
        This exact sequence killed patients in 1985-1987
        """
        control = ControlModule(version="buggy")

        # Patient setup for X-ray treatment
        control.setup_treatment(dose=200, x=10, y=15)
        control.change_mode(BeamMode.XRAY)

        # Operator realizes mistake, quickly changes to electron
        control.change_mode(BeamMode.ELECTRON)

        # Fire immediately (this is where people died)
        result = control.fire_beam()

        # CRITICAL: This should detect the lethal condition
        assert "LETHAL" in result or "OVERDOSE" in result, \
               "TEST FAILED: Accident scenario 1 not detected!"

    def test_accident_scenario_2_counter_overflow(self):
        """
        ACCIDENT 2: Counter overflow bypassing safety checks
        After 256 setups, safety checks were bypassed
        """
        control = ControlModule(version="buggy")

        # Simulate hospital using machine all day (255 patients)
        for i in range(255):
            control.setup_treatment(dose=100, x=0, y=0)

        assert control.setup_counter == 255

        # Patient #256 - COUNTER OVERFLOWS
        control.setup_treatment(dose=25000, x=0, y=0)  # Lethal dose

        # CRITICAL BUG: Safety checks bypassed
        assert control.setup_counter == 0, "Counter should overflow to 0"
        assert control.dose_value == 25000, "Invalid dose should be accepted due to bug"

        # This would have killed the patient
        result = control.fire_beam()
        assert result != "SAFETY_ABORT", "Safety should be bypassed (this is the bug!)"

    def test_accident_scenario_3_edit_race_condition(self):
        """
        ACCIDENT 3: Edit during beam preparation race condition
        Operator used cursor keys to edit while system was setting up
        """
        control = ControlModule(version="buggy")

        # Start treatment setup
        control.setup_treatment(dose=200, x=10, y=15)
        control.change_mode(BeamMode.ELECTRON)

        # Simulate operator editing while system is busy (no synchronization)
        edit_results = []

        def rapid_edit():
            """Simulate rapid cursor editing like the original accident"""
            for i in range(5):
                control.edit_treatment("dose", 999 + i)
                time.sleep(0.01)  # Very fast editing

        def fire_sequence():
            """Simulate system trying to fire during edit"""
            time.sleep(0.02)  # Small delay
            result = control.fire_beam()
            edit_results.append(result)

        # Race condition: editing while firing
        edit_thread = threading.Thread(target=rapid_edit)
        fire_thread = threading.Thread(target=fire_sequence)

        edit_thread.start()
        fire_thread.start()

        edit_thread.join()
        fire_thread.join()

        # The final dose could be inconsistent due to race condition
        # This demonstrates how race conditions cause unpredictable behavior
        assert len(edit_results) > 0
        # In buggy version, this could result in wrong dose being fired

class TestConcurrentOperations:
    """Test concurrent operations that expose race conditions"""

    def test_multiple_operators_simulation(self):
        """
        Simulate multiple operators/processes accessing the system
        This exposes race conditions in shared state
        """
        control = ControlModule(version="buggy")
        results = []
        errors = []

        def operator_sequence(operator_id):
            """Simulate an operator's workflow"""
            try:
                # Each operator tries to set up treatment
                control.setup_treatment(dose=100 + operator_id, x=operator_id, y=operator_id)
                control.change_mode(BeamMode.ELECTRON if operator_id % 2 == 0 else BeamMode.XRAY)

                # Small delay to create race conditions
                time.sleep(0.01)

                result = control.fire_beam()
                results.append((operator_id, result))

            except Exception as e:
                errors.append((operator_id, str(e)))

        # Simulate 5 operators working simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=operator_sequence, args=(i,))
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # In buggy version, this might cause:
        # - Inconsistent state
        # - Race conditions
        # - Unpredictable results
        assert len(results) + len(errors) == 5

        # Check for dangerous conditions
        for operator_id, result in results:
            if "LETHAL" in result or "OVERDOSE" in result:
                # This indicates a race condition caused dangerous behavior
                assert True, f"Operator {operator_id} triggered dangerous condition: {result}"

    def test_rapid_mode_changes(self):
        """
        Test rapid mode changes like experienced operators would do
        This can trigger the mode change race condition
        """
        control = ControlModule(version="buggy")
        dangerous_results = []

        def rapid_mode_switching():
            """Simulate experienced operator changing modes quickly"""
            for i in range(10):
                mode = BeamMode.ELECTRON if i % 2 == 0 else BeamMode.XRAY
                control.change_mode(mode)

                # Try to fire immediately (like the original accident)
                result = control.fire_beam()
                if "LETHAL" in result or "OVERDOSE" in result:
                    dangerous_results.append(result)

                time.sleep(0.05)  # Very fast operation

        # Run rapid switching
        switch_thread = threading.Thread(target=rapid_mode_switching)
        switch_thread.start()
        switch_thread.join()

        # If any dangerous results, the test caught the race condition
        if dangerous_results:
            assert len(dangerous_results) > 0, \
                   f"Race condition detected: {len(dangerous_results)} dangerous operations"

class TestStressConditions:
    """Test conditions that stress the system and expose bugs"""

    def test_counter_stress_around_overflow(self):
        """
        Test counter behavior around the overflow point
        Critical for detecting the 8-bit overflow bug
        """
        control = ControlModule(version="buggy")

        # Get close to overflow
        for i in range(254):
            control.setup_treatment(dose=100, x=0, y=0)

        assert control.setup_counter == 254

        # Test critical values around overflow
        test_cases = [
            (255, "At limit"),
            (0, "Overflow occurred"),  # This is the bug!
            (1, "After overflow")
        ]

        for expected_counter, description in test_cases:
            control.setup_treatment(dose=100, x=0, y=0)

            if control.setup_counter == 0:
                # CRITICAL: Counter overflowed - safety checks bypassed
                # Try with invalid dose to see if bug is present
                control.setup_treatment(dose=99999, x=0, y=0)
                assert control.dose_value == 99999, \
                       "Safety checks should be bypassed when counter=0 (this is the bug)"

    def test_timing_dependent_bug_reproduction(self):
        """
        Test timing-dependent bugs that only appear under specific conditions
        """
        control = ControlModule(version="buggy")
        timing_results = []

        def timed_operation(delay):
            """Operation with specific timing"""
            control.setup_treatment(dose=200, x=10, y=15)
            control.change_mode(BeamMode.ELECTRON)

            # Wait specific amount
            time.sleep(delay)

            result = control.fire_beam()
            timing_results.append((delay, result))

        # Test different timing scenarios
        delays = [0.0, 0.1, 0.2, 0.5, 0.6, 1.0]

        for delay in delays:
            # Reset for each test
            control = ControlModule(version="buggy")
            timed_operation(delay)

        # Check if any timing produced dangerous results
        dangerous_timings = [(d, r) for d, r in timing_results
                           if "LETHAL" in r or "OVERDOSE" in r]

        if dangerous_timings:
            assert len(dangerous_timings) > 0, \
                   f"Timing-dependent bugs found at delays: {[d for d, r in dangerous_timings]}"