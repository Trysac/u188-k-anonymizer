# Testing

## Policy
- The package maintains high test coverage. The CI gate fails if branch coverage of `src/k_anonymizer` falls below 80%.
- Tests are deterministic, relying on no network, no external clock, and independent test ordering.
- Every bug report must be accompanied by a failing test that reproduces the error.

## Test Coverage
- `tests/test_k_anonymizer.py`: Exercises the public API including all successful flows, validation errors (missing columns, invalid options, etc.), and lattice traversal logic.
- The test suite directly verifies the requirements listed in the specification, such as k-anonymity calculations on small sample sets and the mapping behavior of hierarchies (numeric_range and prefix_mask).
