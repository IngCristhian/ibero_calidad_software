/**
 * k6 Load Test: Counter Overflow Stress Test
 * Specifically tests the 8-bit counter overflow bug that bypassed safety checks
 * Simulates extended hospital use that triggers the 256+ setup overflow
 */

import { check, sleep } from 'k6';
import exec from 'k6/execution';

export const options = {
  scenarios: {
    overflow_test: {
      executor: 'per-vu-iterations',
      vus: 1, // Single user to maintain counter state
      iterations: 1, // Single test that does 300+ setups
      maxDuration: '10m',
    },
  },
  thresholds: {
    checks: ['rate>0.95'],
    // Custom threshold for overflow detection
    'counter_overflow_detected': ['count>0'],
    'safety_bypass_detected': ['count>0'],
  },
};

export default function () {
  console.log('🔢 Starting counter overflow stress test...');

  const result = performOverflowTest();

  const checks = {
    'Counter overflow reproduced': (r) => r.includes('OVERFLOW_DETECTED'),
    'Safety bypass confirmed': (r) => r.includes('SAFETY_BYPASS'),
    'Critical bug present': (r) => r.includes('COUNTER_0'),
  };

  check(result, checks);

  console.log('📊 Overflow test completed');
}

function performOverflowTest() {
  console.log('🏥 Simulating busy hospital day - 300+ patients...');

  try {
    const { execSync } = require('child_process');

    const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule, BeamMode
import time

print('Starting overflow stress test...')
c = ControlModule('buggy')

# Track critical counter values
critical_points = []
safety_bypasses = []
overflow_detected = False

# Simulate 300 patients to force counter overflow
for patient in range(1, 301):
    # Each patient setup increments counter
    result = c.setup_treatment(
        dose=200 + (patient % 100),  # Vary dose
        x=patient % 50,
        y=patient % 30
    )

    current_counter = c.setup_counter

    # Track critical points around overflow
    if current_counter in [253, 254, 255, 0, 1, 2]:
        critical_points.append((patient, current_counter))
        print(f'Patient {patient}: Counter = {current_counter}')

    # Test for overflow
    if current_counter == 0 and patient > 255:
        overflow_detected = True
        print(f'OVERFLOW DETECTED at patient {patient}')

        # Test if safety is bypassed when counter = 0
        safety_test = c.setup_treatment(dose=99999, x=0, y=0)  # Invalid dose
        if safety_test and c.dose_value == 99999:
            safety_bypasses.append(patient)
            print(f'SAFETY BYPASS at patient {patient} - invalid dose accepted!')

    # Brief simulation of treatment time
    if patient % 50 == 0:
        print(f'Processed {patient}/300 patients...')

print(f'Test completed. Critical points: {critical_points}')
print(f'Overflow detected: {overflow_detected}')
print(f'Safety bypasses: {len(safety_bypasses)}')

# Return summary
result_parts = []
if overflow_detected:
    result_parts.append('OVERFLOW_DETECTED')
if safety_bypasses:
    result_parts.append('SAFETY_BYPASS')
if any(point[1] == 0 for point in critical_points):
    result_parts.append('COUNTER_0')

result_parts.append(f'CRITICAL_POINTS:{len(critical_points)}')
result_parts.append(f'BYPASSES:{len(safety_bypasses)}')

print(':'.join(result_parts))
"`;

    const result = execSync(command, {
      encoding: 'utf8',
      timeout: 120000,  // 2 minutes timeout
      maxBuffer: 1024 * 1024  // 1MB buffer for output
    });

    return result.trim();

  } catch (error) {
    console.error('❌ Overflow test failed:', error.message);
    return `ERROR: ${error.message}`;
  }
}

// Additional test for specific overflow scenarios
export function testSpecificOverflowScenarios() {
  console.log('🎯 Testing specific overflow scenarios...');

  try {
    const { execSync } = require('child_process');

    const command = `cd /app && python -c "
from src.simulator.control_module import ControlModule
import time

scenarios = []

# Test scenario 1: Exactly at limit (255)
print('Testing counter at 255...')
c1 = ControlModule('buggy')
for i in range(255):
    c1.setup_treatment(100, 0, 0)

scenarios.append(('AT_LIMIT', c1.setup_counter, c1.setup_treatment(100, 0, 0)))

# Test scenario 2: Overflow to 0
print('Testing overflow to 0...')
c2 = ControlModule('buggy')
for i in range(256):
    c2.setup_treatment(100, 0, 0)

# Try invalid dose when counter = 0
invalid_dose_accepted = c2.setup_treatment(50000, 0, 0)
scenarios.append(('OVERFLOW_0', c2.setup_counter, invalid_dose_accepted))

# Test scenario 3: After overflow
print('Testing after overflow...')
c3 = ControlModule('buggy')
for i in range(257):
    c3.setup_treatment(100, 0, 0)

scenarios.append(('AFTER_OVERFLOW', c3.setup_counter, True))

for scenario, counter, result in scenarios:
    print(f'{scenario}:COUNTER_{counter}:RESULT_{result}')

print('SPECIFIC_TESTS_COMPLETED')
"`;

    const result = execSync(command, { encoding: 'utf8', timeout: 30000 });
    return result.trim();

  } catch (error) {
    return `SPECIFIC_ERROR: ${error.message}`;
  }
}

export function handleSummary(data) {
  const checkRate = data.metrics.checks?.values.rate || 0;
  const iterations = data.metrics.iterations?.values.count || 0;

  console.log('\n🔢 THERAC-25 COUNTER OVERFLOW STRESS TEST SUMMARY');
  console.log('==================================================');
  console.log(`Test iterations completed: ${iterations}`);
  console.log(`Overflow detection rate: ${(checkRate * 100).toFixed(1)}%`);

  // Parse results for overflow detection
  const stdout = data.metrics.data_received ?
    Buffer.from(data.metrics.data_received.values.count).toString() : '';

  if (stdout.includes('OVERFLOW_DETECTED')) {
    console.log('💀 CRITICAL: Counter overflow bug confirmed!');
    console.log('📊 This bug bypassed safety checks in the real Therac-25');
  }

  if (stdout.includes('SAFETY_BYPASS')) {
    console.log('⚠️ DANGER: Safety validations bypassed due to overflow');
    console.log('🔧 32-bit counters would prevent this overflow');
  }

  if (stdout.includes('COUNTER_0')) {
    console.log('🎯 BUG REPRODUCED: Counter overflowed to 0');
    console.log('💡 This is the exact bug that killed patients');
  }

  // Recommendations
  console.log('\n🔧 PREVENTION MEASURES:');
  console.log('- Use 32-bit or 64-bit counters instead of 8-bit');
  console.log('- Add explicit overflow checks');
  console.log('- Implement independent safety validation');
  console.log('- Regular counter reset procedures');
  console.log('- Automated alerts at high counter values');

  return {
    'stdout': JSON.stringify(data, null, 2),
    'summary.json': JSON.stringify({
      test_type: 'counter_overflow_stress',
      overflow_detected: stdout.includes('OVERFLOW_DETECTED'),
      safety_bypass_detected: stdout.includes('SAFETY_BYPASS'),
      counter_zero_confirmed: stdout.includes('COUNTER_0'),
      check_success_rate: checkRate,
      iterations: iterations,
      recommendations: [
        'Use 32-bit counters',
        'Add overflow checks',
        'Independent safety validation',
        'Counter reset procedures',
        'High-value alerts'
      ]
    }),
  };
}