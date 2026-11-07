# Security and Privacy Model

## Threat Model
- **Defended:**
    - **Input Resource Exhaustion:** The lattice search is constrained by a `max_nodes` limit (default 10,000) to prevent excessive memory or CPU usage. The CLI rejects files larger than 50,000,000 bytes.
    - **Data Leakage in Exceptions:** Error messages truncate offending cell values to 200 characters to prevent accidental exposure of PII in logs.
    - **Internal Logging:** The package uses `logging.NullHandler` to ensure no raw table data is ever written to standard logs.
- **Not Defended:**
    - **Homogeneity/Background Attacks:** k-anonymity is a property of quasi-identifiers, not sensitive attributes. It does not stop attackers who know that a specific individual has a specific sensitive attribute regardless of their QI group.
    - **Legal Compliance:** Usage of this library does not automatically equate to "anonymization" under GDPR Recital 26 or HIPAA Safe Harbor. It is a technical engineering component, not a legal guarantee.
