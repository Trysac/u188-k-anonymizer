# Architecture

`trysac-k-anonymizer` provides full-domain generalisation (Samarati-style) and k-anonymity verification over tabular datasets represented as sequence of dictionary rows (`list[dict[str, str]]`).

## Core Concepts

1. **Quasi-Identifiers (QIs)**: Attributes (e.g., age, postal code, gender) that, in combination, may re-identify individuals.
2. **Equivalence Classes**: Subsets of rows that share identical quasi-identifier values.
3. **Hierarchy**: Monotonically increasing generalisation steps from level 0 (identity) to `max_level` (fully masked `*`).
   - `numeric_range(widths)`: Partitions integers into intervals of width $w$, e.g. `[lo, lo + w - 1]`.
   - `prefix_mask(length)`: Masks the trailing $i$ characters with `*`.
4. **Lattice Search**: Generates level vectors ordered by total sum (minimal information loss) and broken lexicographically by quasi-identifier order.
5. **Bounded Suppression**: Discards at most $\lfloor \text{max\_suppression} \times N \rfloor$ rows belonging to equivalence classes smaller than $k$.

## Error Handling

All errors inherit from `KAnonError` and expose a typed `code` property:
- `invalid_value`: Cell value cannot be transformed (e.g., non-integer in numeric range).
- `invalid_column`: A specified QI column is missing from rows.
- `invalid_option`: Invalid arguments (e.g., $k < 2$, negative widths, unsorted widths).
- `search_too_large`: The generalisation lattice exceeds `max_nodes` (default 10,000).
- `input_too_large`: Input file exceeds the 50MB limit in CLI.
