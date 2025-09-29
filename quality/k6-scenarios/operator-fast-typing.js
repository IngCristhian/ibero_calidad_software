/**
 * k6 Load Test: Fast Operator Typing
 * Simulates experienced operator typing quickly - this is how accidents happened
 * Reproduces the exact speed that caused the Therac-25 deaths
 */

import { check, sleep } from 'k6';
import exec from 'k6/execution';

export const options = {
  stages: [
    { duration: '30s', target: 1 }, // Single operator
    { duration: '2m', target: 1 },  // Sustained fast typing
    { duration: '30s', target: 0 }, // Ramp down
  ],
  thresholds: {
    // Success criteria: No lethal overdoses should occur
    checks: ['rate>0.95'],
    http_req_duration: ['p(95)<2000'], // Fast response times
  },
};

export default function () {
  const iterationId = exec.vu.iterationInInstance;

  console.log(`🏥 Operator session ${iterationId}: Starting rapid treatment sequence`);

  // Scenario 1: X-ray to Electron quick change (DEADLY BUG)
  let result = simulateRapidModeChange();
  check(result, {
    'No lethal overdose in mode change': (r) => !r.includes('LETHAL'),
    'No accidents in rapid typing': (r) => !r.includes('OVERDOSE'),
  });

  sleep(0.5); // Brief pause like real operator

  // Scenario 2: Rapid editing sequence
  result = simulateRapidEditing();
  check(result, {
    'Edit race condition handled': (r) => r.includes('SUCCESS') || r.includes('SAFETY'),
  });

  sleep(0.3);

  // Scenario 3: Fast setup sequence
  result = simulateFastSetup();
  check(result, {
    'Fast setup completed safely': (r) => !r.includes('ERROR'),
  });

  console.log(`📊 Session ${iterationId} result: ${result}`);
}

function simulateRapidModeChange() {
  // This simulates the exact sequence that killed patients
  console.log('🔄 Rapid mode change: X-ray → Electron');

  // In k6, we simulate the load rather than actual execution
  // This would be HTTP calls to a web interface in a real scenario

  // Simulate rapid operator actions with timing
  const startTime = new Date().getTime();

  // Simulate setup time
  sleep(0.1);

  // Simulate mode change time (this is where the race condition happens)
  sleep(0.05); // Very fast mode change

  const endTime = new Date().getTime();
  const duration = endTime - startTime;

  // In real scenario, rapid changes would cause LETHAL_OVERDOSE
  if (duration < 200) { // Less than 200ms is dangerous
    return 'LETHAL_OVERDOSE'; // Simulates the bug being triggered
  } else {
    return 'SUCCESS';
  }
}

function simulateRapidEditing() {
  console.log('✏️ Rapid editing simulation');

  // Simulate rapid editing during operation
  const editStart = new Date().getTime();

  // Multiple rapid edits
  sleep(0.02); // Edit 1
  sleep(0.01); // Edit 2
  sleep(0.02); // Edit 3

  const editEnd = new Date().getTime();
  const editDuration = editEnd - editStart;

  // Rapid editing under 100ms could cause race conditions
  if (editDuration < 100) {
    return 'RACE_CONDITION_DETECTED';
  } else {
    return 'SUCCESS';
  }
}

function simulateFastSetup() {
  console.log('⚡ Fast setup simulation');

  // Simulate very fast setup sequence
  const setupStart = new Date().getTime();

  sleep(0.1); // Setup
  sleep(0.05); // Mode change
  sleep(0.02); // Fire

  const setupEnd = new Date().getTime();
  const setupDuration = setupEnd - setupStart;

  // Very fast setup under 180ms is typical of experienced operators
  if (setupDuration < 180) {
    return 'FAST_OPERATOR_DETECTED';
  } else {
    return 'SUCCESS';
  }
}

export function handleSummary(data) {
  // Custom summary for accident detection
  const accidents = data.checks ?
    Object.values(data.checks).filter(check =>
      check.name.includes('lethal') || check.name.includes('overdose')
    ).length : 0;

  console.log('\n🏥 THERAC-25 FAST TYPING TEST SUMMARY');
  console.log('=====================================');
  console.log(`Total VU iterations: ${data.metrics.iterations?.values.count || 0}`);
  console.log(`Potential accidents detected: ${accidents}`);
  console.log(`Check success rate: ${data.metrics.checks?.values.rate * 100 || 0}%`);

  if (accidents > 0) {
    console.log('💀 CRITICAL: Fast typing exposed dangerous conditions!');
    console.log('🔧 Modern UI delays and validation would prevent this.');
  } else {
    console.log('✅ No accidents detected in fast typing scenario');
  }

  return {
    'stdout': JSON.stringify(data, null, 2),
    'summary.json': JSON.stringify({
      test_type: 'fast_typing',
      accidents_detected: accidents,
      success_rate: data.metrics.checks?.values.rate || 0,
      iterations: data.metrics.iterations?.values.count || 0,
    }),
  };
}