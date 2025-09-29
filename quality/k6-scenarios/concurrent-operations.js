/**
 * k6 Load Test: Concurrent Operations
 * Simulates multiple operators/processes accessing the system simultaneously
 * Tests for race conditions in shared state access
 */

import { check, sleep } from 'k6';
import exec from 'k6/execution';

export const options = {
  stages: [
    { duration: '15s', target: 3 },  // Ramp up to 3 concurrent users
    { duration: '2m', target: 5 },   // Peak load: 5 operators
    { duration: '1m', target: 8 },   // Stress: 8 concurrent
    { duration: '30s', target: 0 },  // Ramp down
  ],
  thresholds: {
    checks: ['rate>0.90'], // 90% success rate minimum
    http_req_duration: ['p(95)<3000'],
    // Custom threshold for race conditions
    'race_conditions_detected': ['count<5'], // Max 5 race conditions allowed
  },
};

let raceConditionsDetected = 0;

export default function () {
  const vuId = exec.vu.idInInstance;
  const iteration = exec.vu.iterationInInstance;

  console.log(`👥 Operator ${vuId}.${iteration}: Starting concurrent session`);

  // Each VU simulates a different operator workflow
  let workflow = getWorkflowForOperator(vuId);
  let result = executeWorkflow(workflow, vuId);

  // Check for race conditions and dangerous conditions
  const checks = {
    'No lethal conditions': (r) => !r.includes('LETHAL'),
    'No overdose conditions': (r) => !r.includes('OVERDOSE'),
    'No critical errors': (r) => !r.includes('CRITICAL_ERROR'),
    'State consistency maintained': (r) => !r.includes('INCONSISTENT'),
  };

  check(result, checks);

  // Detect race conditions
  if (result.includes('RACE') || result.includes('CONFLICT')) {
    raceConditionsDetected++;
    console.log(`⚠️ Race condition detected by Operator ${vuId}`);
  }

  // Random delay to simulate real operator thinking time
  sleep(Math.random() * 0.5 + 0.2);
}

function getWorkflowForOperator(vuId) {
  // Different operators have different patterns
  const workflows = [
    'experienced_fast',    // VU 1: Fast, experienced operator
    'new_cautious',       // VU 2: New, slower operator
    'emergency_rapid',    // VU 3: Emergency case, very fast
    'routine_editing',    // VU 4: Lots of corrections/edits
    'mode_switching',     // VU 5: Frequent mode changes
  ];

  return workflows[vuId % workflows.length];
}

function executeWorkflow(workflow, vuId) {
  try {
    switch (workflow) {
      case 'experienced_fast':
        return executeExperiencedFast(vuId);

      case 'new_cautious':
        return executeNewCautious(vuId);

      case 'emergency_rapid':
        return executeEmergencyRapid(vuId);

      case 'routine_editing':
        return executeRoutineEditing(vuId);

      case 'mode_switching':
        return executeModeSwitching(vuId);

      default:
        return executeStandardWorkflow(vuId);
    }
  } catch (error) {
    return `ERROR_${workflow}: ${error.message}`;
  }
}

function executeExperiencedFast(vuId) {
  console.log(`🏃‍♂️ Operator ${vuId}: Experienced fast workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import time
import threading

c = ControlModule('buggy')

# Fast setup like experienced operator
c.setup_treatment(${200 + vuId * 10}, ${vuId * 5}, ${vuId * 3})

# Quick mode changes (this is dangerous!)
c.change_mode(BeamMode.XRAY)
time.sleep(0.05)  # Very brief pause
c.change_mode(BeamMode.ELECTRON)

# Fire immediately
result = c.fire_beam()
print(f'OPERATOR_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 8000 });
  return result.trim();
}

function executeEmergencyRapid(vuId) {
  console.log(`🚨 Operator ${vuId}: Emergency rapid workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import threading
import time

c = ControlModule('buggy')

# Emergency case - no time for delays
c.setup_treatment(300, ${vuId * 2}, ${vuId * 4})
c.change_mode(BeamMode.ELECTRON)

# Immediate fire (emergency situations cause accidents)
result = c.fire_beam()
print(f'EMERGENCY_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 6000 });
  return result.trim();
}

function executeRoutineEditing(vuId) {
  console.log(`✏️ Operator ${vuId}: Routine editing workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import threading
import time

c = ControlModule('buggy')

# Initial setup
c.setup_treatment(250, 10, 15)

# Multiple edits (creates race conditions)
def edit1():
    time.sleep(0.02)
    c.edit_treatment('dose', ${400 + vuId * 50})

def edit2():
    time.sleep(0.05)
    c.edit_treatment('position_x', ${vuId * 7})

# Start concurrent edits
t1 = threading.Thread(target=edit1)
t2 = threading.Thread(target=edit2)
t1.start()
t2.start()

# Try to fire while editing (DANGEROUS)
time.sleep(0.03)
result = c.fire_beam()

t1.join()
t2.join()

print(f'EDITING_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 10000 });
  return result.trim();
}

function executeModeSwitching(vuId) {
  console.log(`🔄 Operator ${vuId}: Mode switching workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import time

c = ControlModule('buggy')

# Setup
c.setup_treatment(275, ${vuId * 6}, ${vuId * 8})

# Rapid mode switches (causes race conditions)
modes = [BeamMode.XRAY, BeamMode.ELECTRON, BeamMode.XRAY, BeamMode.ELECTRON]
for mode in modes:
    c.change_mode(mode)
    time.sleep(0.02)  # Very short delay

# Fire after rapid switches
result = c.fire_beam()
print(f'SWITCHING_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 8000 });
  return result.trim();
}

function executeStandardWorkflow(vuId) {
  console.log(`📋 Operator ${vuId}: Standard workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode

c = ControlModule('buggy')
c.setup_treatment(${225 + vuId * 15}, ${vuId * 4}, ${vuId * 5})
c.change_mode(BeamMode.ELECTRON)
result = c.fire_beam()
print(f'STANDARD_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 5000 });
  return result.trim();
}

function executeNewCautious(vuId) {
  console.log(`🐌 Operator ${vuId}: New cautious workflow`);

  const { execSync } = require('child_process');

  const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import time

c = ControlModule('buggy')

# Slow, careful setup
c.setup_treatment(180, ${vuId * 3}, ${vuId * 2})
time.sleep(0.2)  # Cautious pause

c.change_mode(BeamMode.ELECTRON)
time.sleep(0.3)  # Another pause

result = c.fire_beam()
print(f'CAUTIOUS_${vuId}:{result}')
"`;

  const result = execSync(command, { encoding: 'utf8', timeout: 8000 });
  return result.trim();
}

export function handleSummary(data) {
  const totalIterations = data.metrics.iterations?.values.count || 0;
  const checkRate = data.metrics.checks?.values.rate || 0;
  const avgDuration = data.metrics.http_req_duration?.values.avg || 0;

  console.log('\n👥 THERAC-25 CONCURRENT OPERATIONS TEST SUMMARY');
  console.log('===============================================');
  console.log(`Total concurrent sessions: ${totalIterations}`);
  console.log(`Race conditions detected: ${raceConditionsDetected}`);
  console.log(`Safety check success rate: ${(checkRate * 100).toFixed(1)}%`);
  console.log(`Average operation time: ${avgDuration.toFixed(0)}ms`);

  if (raceConditionsDetected > 0) {
    console.log('⚠️ RACE CONDITIONS DETECTED!');
    console.log('🔧 Proper synchronization (mutexes, locks) would prevent this.');
  }

  if (checkRate < 0.95) {
    console.log('💀 SAFETY FAILURES DETECTED!');
    console.log('🔧 Comprehensive testing would have caught these bugs.');
  }

  return {
    'stdout': JSON.stringify(data, null, 2),
    'summary.json': JSON.stringify({
      test_type: 'concurrent_operations',
      race_conditions: raceConditionsDetected,
      safety_success_rate: checkRate,
      total_sessions: totalIterations,
      avg_duration_ms: avgDuration,
    }),
  };
}