// Rust adapter feature test (CodeLLDB).
//
// Build with `cargo build` first, then launch `target/debug/rust-demo`.
// Run normally to see three wrong results; run with `--hang` to exercise the
// `pause` control on an infinite loop.

// apply_discount returns price after a percent discount.
//
// BUG: the sign is backwards — it adds the discount instead of subtracting it.
// Exercise step_in/step_out: breakpoint on the call in main, step_in, snapshot
// price/percent, then step_out.
fn apply_discount(price: f64, percent: f64) -> f64 {
    price * (1.0 + percent / 100.0)
}

// sum_even returns the sum of the first n even numbers (0 + 2 + ... + 2*(n-1)).
//
// BUG: off-by-one — `<=` runs one iteration too many. Exercise
// breakpoint + snapshot on the `total +=` line.
fn sum_even(n: u32) -> u32 {
    let mut total = 0;
    for i in 0..=n {
        total += 2 * i;
    }
    total
}

// process doubles each input value.
//
// BUG (run_to_line target): the line `result[last] += 1000` corrupts the last
// element. Use run_to_line straight to it (no breakpoint).
fn process(values: &[i32]) -> Vec<i32> {
    let mut result: Vec<i32> = values.iter().map(|v| v * 2).collect();
    let last = result.len() - 1;
    result[last] += 1000;
    result
}

// find_divisor hangs because the loop counter never advances.
//
// BUG: missing `i += 1`. Run with `--hang`, then use the `pause` control.
// The `mut` is kept for the corrected version, so silence the resulting warning.
#[allow(unused_mut)]
fn find_divisor(n: u32) -> i32 {
    let mut i = 2;
    while i < n {
        if n % i == 0 {
            return i as i32;
        }
        // BUG: missing i += 1
    }
    -1
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--hang") {
        println!("hanging... (use the debugger 'pause')");
        find_divisor(9);
        return;
    }

    println!(
        "apply_discount(100, 20) = {} (expected 80)",
        apply_discount(100.0, 20.0)
    );
    println!("sum_even(5) = {} (expected 20)", sum_even(5));
    println!(
        "process([1,2,3]) = {:?} (expected [2, 4, 6])",
        process(&[1, 2, 3])
    );
}
