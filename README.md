# k-anonymizer

Check k-anonymity of tabular data and find minimal full-domain generalisation levels with bounded suppression.

## The Problem
Teams sharing extracts for analytics or research often remove explicit identifiers but keep quasi-identifiers (such as age, postcode, and gender) which, in combination, frequently re-identify individuals. While measuring k-anonymity and generalising columns is a standard defense, existing tools are often heavy desktop research suites.

`k-anonymizer` is a zero-dependency, pure Python package designed for automated pipelines, continuous integration, and unit tests.

## Why not ARX or other desktop suites?
Existing anonymisation tools like ARX are desktop research suites that introduce heavy JVM dependencies and complex GUIs. `k-anonymizer` is a lightweight, dependency-free library for Python that integrates directly into your data processing scripts and testing suites.

## Installation
```bash
pip install k-anonymizer
```

## Usage Example
```python
from k_anonymizer import check_k, anonymize, numeric_range, prefix_mask

rows = [{"age": "34", "zip": "28013"}, {"age": "36", "zip": "28014"}]
# Verify current k-anonymity
print(check_k(rows, ["age", "zip"]).k_actual)
# Perform full-domain generalisation
res = anonymize(rows, {"age": numeric_range([10, 20]), "zip": prefix_mask(5)}, k=2)
print(res.levels, res.k_actual)
```

## Public API Summary
- `check_k(rows, qi)`: Calculates `KReport` (k_actual, classes, smallest_classes).
- `anonymize(rows, hierarchies, k, max_suppression, max_nodes)`: Returns `Result` with generalized rows and suppression stats.
- `numeric_range(widths)`: Hierarchy for numeric data; requires strictly increasing positive widths.
- `prefix_mask(length)`: Hierarchy masking trailing characters.
- `KAnonError`: Raised with codes: `invalid_value`, `invalid_column`, `invalid_option`, `search_too_large`, `input_too_large`.

## Important Notices
- **Security Limitations:** k-anonymity does not protect against homogeneity or background-knowledge attacks. For those, you need l-diversity or t-closeness.
- **Legal:** This library is a technical tool. It does not guarantee data anonymisation under GDPR Recital 26 or similar laws and does not constitute legal advice.

See [docs/SECURITY.md](docs/SECURITY.md) for a detailed threat model.
