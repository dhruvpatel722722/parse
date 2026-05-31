# Broken Package Resolver

A package manager's resolver daemon crashed mid-operation, leaving behind its internal database files. Your job is to reconstruct the correct installation order that the resolver would have produced.

## Data Files

The data is located in `/app/data/` and consists of:

1. **`packages.db`** — Binary package database containing package names, versions, priority tiers, and virtual provides declarations.
   - Format: 4-byte magic `PKDB`, 4-byte LE package count, then per package:
     - 2-byte LE name length, name bytes
     - 2-byte LE version length, version string
     - 1-byte tier (priority level)
     - 4-byte LE installed size
     - 2-byte LE provides count, then per provide: 2-byte LE length, provide name

2. **`dependencies.txt`** — Human-readable dependency declarations in format:
   `package: dep1 (>= version), dep2 (>= version), ...`

3. **`conflicts.conf`** — Mutual exclusion declarations. Packages on the same line cannot coexist.

4. **`resolver.conf`** — Documentation of the resolution algorithm.

## Task

Implement the package resolution algorithm described in `resolver.conf` and produce the correct installation order.

Write the output to `/app/output/install_order.txt` — one package name per line, in the exact order they would be installed. Only include packages that are successfully installed (not skipped due to conflicts, and not deadlocked due to unsatisfiable dependencies).

## Important Notes

- Versions use **epoch-based comparison**: format is `[epoch:]major.minor.patch`. If no epoch prefix, epoch is 0. Epochs dominate: `2:0.1.0` is newer than `1:99.99.99`.
- Virtual packages (e.g., `virtual-runtime`) are satisfied by any installed package that declares it in its `provides` list.
- The resolver processes packages iteratively — one package per step — and order matters because conflicts are resolved on a first-installed-wins basis.
- Some packages may have unsatisfiable dependencies and will never be installed.
