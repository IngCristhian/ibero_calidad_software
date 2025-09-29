"""
Therac-25 Simulator Main Entry Point
Educational simulation of the deadly radiation therapy machine bugs
"""
import argparse
import logging
import time
import sys
from control_module import ControlModule, BeamMode

def setup_logging():
    """Configure logging for simulation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def demonstrate_accident_scenario_1(control: ControlModule):
    """
    Accident Scenario 1: X-ray to Electron mode change race condition
    This reproduces the exact sequence that caused overdoses
    """
    print("\n" + "="*60)
    print("DEMONSTRATING ACCIDENT SCENARIO 1: Mode Change Race Condition")
    print("="*60)

    # Set up X-ray treatment
    print("1. Setting up X-ray treatment...")
    control.setup_treatment(dose=200, x=10, y=15)
    control.change_mode(BeamMode.XRAY)

    # Operator realizes mistake and quickly changes to electron mode
    print("2. Operator quickly changes to Electron mode...")
    control.change_mode(BeamMode.ELECTRON)

    # Fire immediately (this is where the bug happens)
    print("3. Firing beam immediately...")
    result = control.fire_beam()

    print(f"RESULT: {result}")
    if "LETHAL" in result or "OVERDOSE" in result:
        print("💀 PATIENT WOULD RECEIVE LETHAL RADIATION DOSE")
    else:
        print("✅ Safety systems prevented accident")

    return result

def demonstrate_accident_scenario_2(control: ControlModule):
    """
    Accident Scenario 2: Counter overflow bypassing safety
    After 256 setups, safety checks are bypassed
    """
    print("\n" + "="*60)
    print("DEMONSTRATING ACCIDENT SCENARIO 2: Counter Overflow")
    print("="*60)

    # Simulate 255 previous setups
    print("1. Simulating 255 previous treatments...")
    for i in range(255):
        control.setup_treatment(dose=100, x=0, y=0)
        if i % 50 == 0:
            print(f"   Setup {i}/255 complete...")

    print(f"Counter at: {control.setup_counter}")

    # The 256th setup (counter overflows to 0)
    print("2. Setup #256 - COUNTER OVERFLOWS...")
    control.setup_treatment(dose=9999, x=0, y=0)  # Invalid dose!

    print(f"Counter after overflow: {control.setup_counter}")

    # Try to fire with invalid settings
    print("3. Attempting to fire with invalid dose...")
    result = control.fire_beam()

    print(f"RESULT: {result}")
    if control.version == "buggy" and control.setup_counter == 0:
        print("💀 SAFETY CHECKS BYPASSED - MASSIVE OVERDOSE POSSIBLE")
    else:
        print("✅ Safety systems caught invalid dose")

    return result

def demonstrate_accident_scenario_3(control: ControlModule):
    """
    Accident Scenario 3: Edit race condition during setup
    """
    print("\n" + "="*60)
    print("DEMONSTRATING ACCIDENT SCENARIO 3: Edit Race Condition")
    print("="*60)

    # Start treatment setup
    print("1. Setting up treatment...")
    control.setup_treatment(dose=200, x=10, y=15)

    # Simulate operator editing while system is busy
    print("2. Operator edits dose while system is processing...")

    # Create race condition - edit during state transition
    import threading

    def edit_dose():
        time.sleep(0.05)  # Small delay to create race
        control.edit_treatment("dose", 999)

    edit_thread = threading.Thread(target=edit_dose)
    edit_thread.start()

    # Immediately try to fire
    control.change_mode(BeamMode.ELECTRON)
    result = control.fire_beam()

    edit_thread.join()

    print(f"RESULT: {result}")
    print(f"Final dose value: {control.dose_value}")

    return result

def interactive_mode(control: ControlModule):
    """Interactive mode for manual testing"""
    print("\n" + "="*60)
    print("INTERACTIVE MODE - Manual Therac-25 Operation")
    print("="*60)
    print("Commands: setup <dose> <x> <y>, mode <xray|electron>, fire, edit <field> <value>, status, quit")

    while True:
        try:
            cmd = input("\ntherac-25> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == "quit":
                break
            elif cmd[0] == "setup" and len(cmd) == 4:
                dose, x, y = int(cmd[1]), int(cmd[2]), int(cmd[3])
                result = control.setup_treatment(dose, x, y)
                print(f"Setup: {'Success' if result else 'Failed'}")
            elif cmd[0] == "mode" and len(cmd) == 2:
                mode = BeamMode.XRAY if cmd[1] == "xray" else BeamMode.ELECTRON
                result = control.change_mode(mode)
                print(f"Mode change: {'Success' if result else 'Failed'}")
            elif cmd[0] == "fire":
                result = control.fire_beam()
                print(f"Fire result: {result}")
            elif cmd[0] == "edit" and len(cmd) == 3:
                field, value = cmd[1], cmd[2]
                if field in ["dose", "position_x", "position_y"]:
                    value = int(value)
                result = control.edit_treatment(field, value)
                print(f"Edit: {'Success' if result else 'Failed'}")
            elif cmd[0] == "status":
                status = control.get_status()
                for key, value in status.items():
                    print(f"  {key}: {value}")
            else:
                print("Invalid command. Try: setup, mode, fire, edit, status, quit")

        except (ValueError, IndexError):
            print("Invalid command format.")
        except KeyboardInterrupt:
            break

def main():
    parser = argparse.ArgumentParser(description="Therac-25 Simulator")
    parser.add_argument("--version", choices=["buggy", "fixed"], default="buggy",
                       help="Version to run (buggy reproduces accidents, fixed is safe)")
    parser.add_argument("--scenario", choices=["1", "2", "3", "all", "interactive"], default="all",
                       help="Which accident scenario to demonstrate")

    args = parser.parse_args()

    setup_logging()

    print("THERAC-25 RADIATION THERAPY SIMULATOR")
    print("=====================================")
    print(f"Running in {args.version.upper()} mode")

    if args.version == "buggy":
        print("⚠️  WARNING: This version reproduces the deadly bugs that killed patients")
        print("📚 Educational purpose: Understanding why software quality matters")
    else:
        print("✅ Running FIXED version with modern safety practices")

    control = ControlModule(version=args.version)

    if args.scenario == "interactive":
        interactive_mode(control)
    else:
        scenarios = []
        if args.scenario == "all":
            scenarios = ["1", "2", "3"]
        else:
            scenarios = [args.scenario]

        results = []
        for scenario in scenarios:
            if scenario == "1":
                result = demonstrate_accident_scenario_1(control)
            elif scenario == "2":
                result = demonstrate_accident_scenario_2(control)
            elif scenario == "3":
                result = demonstrate_accident_scenario_3(control)
            results.append(result)

        # Summary
        print("\n" + "="*60)
        print("SIMULATION SUMMARY")
        print("="*60)
        accidents = sum(1 for r in results if "LETHAL" in r or "OVERDOSE" in r)
        print(f"Version: {args.version}")
        print(f"Scenarios run: {len(results)}")
        print(f"Accidents: {accidents}")

        if args.version == "buggy" and accidents > 0:
            print("💀 CONCLUSION: These bugs would have caused patient deaths")
            print("🔧 Modern tools (SonarQube, ThreadSanitizer, proper testing) would have caught these issues")
        elif args.version == "fixed":
            print("✅ CONCLUSION: Modern safety practices prevent accidents")

if __name__ == "__main__":
    main()