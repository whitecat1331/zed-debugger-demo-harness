// TypeScript adapter feature test (vscode-js-debug / pwa-node, source maps).
//
// Compile first so the adapter has JavaScript + source maps to run:
//   npm install && npm run build      # produces dist/main.js + dist/main.js.map
//
// Launch the compiled `dist/main.js`; source maps map breakpoints set in this
// .ts file back to the running .js. Run normally to see three wrong results;
// run the compiled output with `--hang` to exercise the `pause` control.

function applyDiscount(price: number, percent: number): number {
  // BUG: the sign is backwards — adds instead of subtracting (step_in target).
  return price * (1 + percent / 100);
}

function sumEven(n: number): number {
  let total = 0;
  // BUG: off-by-one — `<=` runs one iteration too many.
  for (let i = 0; i <= n; i++) {
    total += 2 * i;
  }
  return total;
}

// processValues doubles each input value.
//
// BUG (run_to_line target): the line `result[result.length - 1] += 1000`
// corrupts the last element. Use run_to_line straight to it (no breakpoint).
//
// Named `processValues` (not `process`) to avoid shadowing Node's global
// `process` object.
function processValues(values: number[]): number[] {
  const result = values.map((v) => v * 2);
  result[result.length - 1] += 1000;
  return result;
}

// findDivisor hangs because the loop counter never advances.
//
// BUG: missing `i++`. Run with `--hang`, then use the `pause` control.
function findDivisor(n: number): number {
  let i = 2;
  while (i < n) {
    if (n % i === 0) return i;
    // BUG: missing i++
  }
  return -1;
}

if (process.argv.includes("--hang")) {
  console.log("hanging... (use the debugger 'pause')");
  findDivisor(9);
} else {
  console.log("applyDiscount(100, 20) =", applyDiscount(100, 20), "(expected 80)");
  console.log("sumEven(5) =", sumEven(5), "(expected 20)");
  console.log("processValues([1,2,3]) =", processValues([1, 2, 3]), "(expected [2,4,6])");
}
