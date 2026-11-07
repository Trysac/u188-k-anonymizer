# k-anonymizer

[![PyPI version](https://img.shields.io/pypi/v/trysac-k-anonymizer)](https://pypi.org/project/trysac-k-anonymizer/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-k-anonymizer)](LICENSE)
[![CI](https://github.com/Trysac/u188-k-anonymizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u188-k-anonymizer/actions/workflows/ci.yml)

Check k-anonymity of tabular data over quasi-identifiers and find minimal full-domain generalisation levels with bounded suppression

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-k-anonymizer
# or
uv add trysac-k-anonymizer
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import k_anonymizer

# normalize() trims surrounding whitespace and lower-cases the text.
print(k_anonymizer.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    k_anonymizer.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
