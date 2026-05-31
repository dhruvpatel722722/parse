# Broken Package Resolver

A package manager's resolver crashed, leaving its database files. Reconstruct the correct installation order.

## Data Files

Located in `/app/data/`:

1. **`packages.db`** — Binary database: 4-byte magic `PKDB`, 4-byte LE count, then per package:
   - 2-byte LE name length, name, 2-byte LE version length, version, 1-byte tier, 4-byte LE size
   - 2-byte LE provides count, then per provide: 2-byte LE length, name

2. **`dependencies.txt`** — Format: `package: dep1 (>= version), dep2 (>= version), ...`

3. **`conflicts.conf`** — Mutual exclusions: `pkg1 <-> pkg2`

4. **`resolver.conf`** — Full algorithm documentation.

## Task

Implement the resolution algorithm from `resolver.conf`. Write output to `/app/output/install_order.txt` — one package name per line, in exact install order. Only include successfully installed packages.

## Key Rules

- **Epoch versioning**: format `[epoch:]major.minor.patch`. No epoch means epoch 0. Epochs dominate: `2:0.1.0` > `1:99.99.99`.
- **Virtual provides**: dependency on `virtual-X` satisfied if any installed package declares it in provides. Version not checked for virtuals.
- **Iterative resolution**: one package per step. Priority: lowest tier → highest version (epoch-aware) → alphabetical name.
- **Conflicts**: first-installed-wins; conflicting packages permanently skipped.
- **Deadlocks**: packages with unsatisfiable deps are never installed.
