# Changelog

## [Unreleased]

- Fix: `compute_discounted_total` was ignoring the `discount_rate` argument.
  The discount is now correctly applied to the accumulated subtotal before
  returning the final order total.
