# Full-domain generalisation search with bounded suppression

Status: accepted (generated, pending human review)

## Context

Tabular datasets need minimal generalisation across multiple quasi-identifier columns to satisfy k-anonymity without excessive data loss, while allowing a strictly bounded fraction of outliers to be suppressed.

## Decision

Implement Samarati-style full-domain generalisation by enumerating lattice level vectors sorted by total sum (information loss) and lexicographically by quasi-identifier order, terminating at the first vector where suppression is at or below floor(max_suppression * len(rows)). Pre-cache generalized column values to ensure deterministic linear-time checks per node.

## Consequences

Search is exact, deterministic, and predictable. Lattice size is bounded by max_nodes (default 10,000) to protect against combinatorial explosion.
