#!/usr/bin/env python3
"""
Generate a corrupted package manager database for the broken-package-resolver task.

The database has 50 packages with:
- Version-conditional dependencies (A depends on B >= version)
- Mutual exclusion / conflict constraints
- Virtual provides (A provides virtual-X, satisfying deps on X)
- Epoch-based versioning (epoch:version, epoch takes priority)
- Priority tiers that affect resolution order
- A specific deterministic resolution algorithm

The agent must produce the correct install order by implementing the resolution algorithm.
"""

import json
import os
import random
import struct
import hashlib

random.seed(98765)

# ============================================================================
# PACKAGE DEFINITIONS
# ============================================================================

# Package names - mix of realistic and slightly confusing names
PKG_NAMES = [
    "libcore", "libnet", "libcrypto", "libfs", "libui",
    "libmath", "liblog", "libthread", "libmem", "libio",
    "sysbase", "sysnet", "sysproc", "sysauth", "syskern",
    "appserver", "appweb", "appcli", "appgui", "appdb",
    "drvnet", "drvfs", "drvgpu", "drvaudio", "drvusb",
    "utilzip", "utiltar", "utilhash", "utilenc", "utilfmt",
    "fwcore", "fwnet", "fwauth", "fwlog", "fwcache",
    "plughttp", "plugftp", "plugssh", "plugdns", "plugsmtp",
    "extjson", "extxml", "extcsv", "extyaml", "exttoml",
    "modstats", "modgraph", "modml", "modviz", "modsched"
]

# Epoch-based versions: "epoch:major.minor.patch" or just "major.minor.patch" (epoch=0)
# The trick: epoch comparison takes absolute priority over version numbers
# So "2:0.1.0" > "1:99.99.99" > "0:99.99.99" > "5.0.0" (no epoch = epoch 0)
def make_version(epoch=0, major=1, minor=0, patch=0):
    if epoch > 0:
        return f"{epoch}:{major}.{minor}.{patch}"
    return f"{major}.{minor}.{patch}"

def parse_version(v):
    """Parse version string into (epoch, major, minor, patch) tuple."""
    if ':' in v:
        epoch_str, rest = v.split(':', 1)
        epoch = int(epoch_str)
    else:
        epoch = 0
        rest = v
    parts = rest.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (epoch, major, minor, patch)

def version_compare(v1, v2):
    """Compare two version strings. Returns -1, 0, or 1."""
    t1 = parse_version(v1)
    t2 = parse_version(v2)
    if t1 < t2: return -1
    if t1 > t2: return 1
    return 0

def version_satisfies(installed_ver, constraint_op, constraint_ver):
    """Check if installed_ver satisfies the constraint."""
    cmp = version_compare(installed_ver, constraint_ver)
    if constraint_op == ">=": return cmp >= 0
    if constraint_op == "<=": return cmp <= 0
    if constraint_op == ">": return cmp > 0
    if constraint_op == "<": return cmp < 0
    if constraint_op == "==": return cmp == 0
    if constraint_op == "!=": return cmp != 0
    return False

# ============================================================================
# BUILD PACKAGE DATABASE
# ============================================================================

packages = {}
for i, name in enumerate(PKG_NAMES):
    # Assign versions - some with epochs to create traps
    if i % 7 == 0:
        # Epoch 2 packages - look "old" version-wise but epoch makes them "new"
        ver = make_version(epoch=2, major=0, minor=random.randint(1,5), patch=random.randint(0,9))
    elif i % 11 == 0:
        # Epoch 1 packages
        ver = make_version(epoch=1, major=random.randint(1,3), minor=random.randint(0,9), patch=random.randint(0,9))
    else:
        # Normal packages
        ver = make_version(epoch=0, major=random.randint(1,8), minor=random.randint(0,15), patch=random.randint(0,20))

    # Priority tiers: 1 (critical/install first) to 5 (optional/install last)
    # Within same tier, alphabetical by name
    tier = (i % 5) + 1

    packages[name] = {
        "version": ver,
        "tier": tier,
        "depends": [],      # [(pkg_name, op, version_constraint)]
        "conflicts": [],    # [pkg_name]
        "provides": [],     # [virtual_name]
        "installed_size": random.randint(100, 50000),
    }

# ============================================================================
# VIRTUAL PROVIDES - packages that satisfy dependencies under alternate names
# ============================================================================

# These create indirection that LLMs struggle with
virtual_provides = {
    "libcore": ["virtual-runtime"],
    "sysbase": ["virtual-runtime", "virtual-init"],
    "syskern": ["virtual-init"],
    "libcrypto": ["virtual-security"],
    "fwauth": ["virtual-security"],
    "libnet": ["virtual-network"],
    "sysnet": ["virtual-network"],
    "drvnet": ["virtual-network"],
    "libui": ["virtual-display"],
    "drvgpu": ["virtual-display"],
    "appgui": ["virtual-display"],
}

for pkg, virtuals in virtual_provides.items():
    packages[pkg]["provides"] = virtuals

# ============================================================================
# DEPENDENCIES - version-conditional with epochs to confuse
# ============================================================================

# Layer 1: Core libs have no deps (tier 1)
# Layer 2: Sys packages depend on libs
# Layer 3: Drivers depend on sys + libs
# Layer 4: Frameworks depend on drivers + sys
# Layer 5: Apps/plugins/ext/mod depend on frameworks + libs

dependencies = [
    # Sys depends on libs
    ("sysbase", "libcore", ">=", "1:0.0.0"),  # Trap: requires epoch >= 1, libcore has epoch 2 so OK
    ("sysnet", "libnet", ">=", "2.0.0"),
    ("sysnet", "virtual-runtime", ">=", "0.0.1"),  # Virtual dep!
    ("sysproc", "libthread", ">=", "1.0.0"),
    ("sysproc", "libmem", ">=", "1.0.0"),
    ("sysauth", "libcrypto", ">=", "1:0.0.0"),  # Requires epoch 1+, libcrypto has epoch 0 BUT fwauth provides virtual-security
    ("sysauth", "virtual-security", ">=", "0.0.1"),
    ("syskern", "libcore", ">=", "2:0.0.0"),  # Requires epoch 2, libcore has epoch 2 - OK
    ("syskern", "libmem", ">=", "1.0.0"),

    # Drivers depend on sys + libs
    ("drvnet", "sysnet", ">=", "1.0.0"),
    ("drvnet", "libio", ">=", "1.0.0"),
    ("drvfs", "sysproc", ">=", "1.0.0"),
    ("drvfs", "libfs", ">=", "1.0.0"),
    ("drvgpu", "syskern", ">=", "1.0.0"),
    ("drvgpu", "libmem", ">=", "2.0.0"),
    ("drvaudio", "syskern", ">=", "1.0.0"),
    ("drvaudio", "libio", ">=", "1.0.0"),
    ("drvusb", "syskern", ">=", "1.0.0"),
    ("drvusb", "libio", ">=", "1.0.0"),

    # Frameworks depend on drivers + sys
    ("fwcore", "sysbase", ">=", "1.0.0"),
    ("fwcore", "virtual-runtime", ">=", "0.0.1"),
    ("fwnet", "drvnet", ">=", "1.0.0"),
    ("fwnet", "fwcore", ">=", "1.0.0"),
    ("fwauth", "sysauth", ">=", "1.0.0"),
    ("fwauth", "libcrypto", ">=", "0.1.0"),  # Note: no epoch requirement here
    ("fwlog", "fwcore", ">=", "1.0.0"),
    ("fwlog", "liblog", ">=", "1.0.0"),
    ("fwcache", "fwcore", ">=", "1.0.0"),
    ("fwcache", "libmem", ">=", "2.0.0"),

    # Utils depend on libs only
    ("utilzip", "libio", ">=", "1.0.0"),
    ("utiltar", "libio", ">=", "1.0.0"),
    ("utiltar", "libfs", ">=", "1.0.0"),
    ("utilhash", "libcrypto", ">=", "0.1.0"),
    ("utilenc", "libcrypto", ">=", "0.1.0"),
    ("utilenc", "virtual-security", ">=", "0.0.1"),
    ("utilfmt", "libio", ">=", "1.0.0"),

    # Plugins depend on frameworks
    ("plughttp", "fwnet", ">=", "1.0.0"),
    ("plughttp", "fwcore", ">=", "1.0.0"),
    ("plugftp", "fwnet", ">=", "1.0.0"),
    ("plugssh", "fwnet", ">=", "1.0.0"),
    ("plugssh", "fwauth", ">=", "1.0.0"),
    ("plugdns", "fwnet", ">=", "1.0.0"),
    ("plugsmtp", "fwnet", ">=", "1.0.0"),
    ("plugsmtp", "plugdns", ">=", "1.0.0"),

    # Extensions depend on utils + libs
    ("extjson", "libio", ">=", "1.0.0"),
    ("extxml", "libio", ">=", "1.0.0"),
    ("extxml", "libmem", ">=", "1.5.0"),
    ("extcsv", "libio", ">=", "1.0.0"),
    ("extyaml", "extjson", ">=", "1.0.0"),
    ("exttoml", "extjson", ">=", "1.0.0"),
    ("exttoml", "utilfmt", ">=", "1.0.0"),

    # Apps depend on everything above
    ("appserver", "fwcore", ">=", "1.0.0"),
    ("appserver", "fwnet", ">=", "1.0.0"),
    ("appserver", "fwlog", ">=", "1.0.0"),
    ("appserver", "plughttp", ">=", "1.0.0"),
    ("appweb", "appserver", ">=", "1.0.0"),
    ("appweb", "extjson", ">=", "1.0.0"),
    ("appweb", "extxml", ">=", "1.0.0"),
    ("appcli", "fwcore", ">=", "1.0.0"),
    ("appcli", "utilfmt", ">=", "1.0.0"),
    ("appgui", "drvgpu", ">=", "1.0.0"),
    ("appgui", "libui", ">=", "1.0.0"),
    ("appgui", "fwcore", ">=", "1.0.0"),
    ("appdb", "fwcache", ">=", "1.0.0"),
    ("appdb", "fwlog", ">=", "1.0.0"),
    ("appdb", "extjson", ">=", "1.0.0"),

    # Modules depend on apps/plugins
    ("modstats", "appdb", ">=", "1.0.0"),
    ("modstats", "extcsv", ">=", "1.0.0"),
    ("modgraph", "modstats", ">=", "1.0.0"),
    ("modgraph", "virtual-display", ">=", "0.0.1"),
    ("modml", "modstats", ">=", "1.0.0"),
    ("modml", "libmath", ">=", "1.0.0"),
    ("modviz", "modgraph", ">=", "1.0.0"),
    ("modviz", "appgui", ">=", "1.0.0"),
    ("modsched", "appserver", ">=", "1.0.0"),
    ("modsched", "libthread", ">=", "1.0.0"),
]

for pkg, dep, op, ver in dependencies:
    packages[pkg]["depends"].append((dep, op, ver))

# ============================================================================
# CONFLICTS - mutual exclusions
# ============================================================================

conflicts = [
    ("plugftp", "plugsmtp"),     # Can't have both (port conflict)
    ("extxml", "extyaml"),       # Parser conflict
    ("drvaudio", "modviz"),      # Resource conflict (DMA channel)
]

for pkg1, pkg2 in conflicts:
    packages[pkg1]["conflicts"].append(pkg2)
    packages[pkg2]["conflicts"].append(pkg1)

# ============================================================================
# RESOLUTION ALGORITHM
# ============================================================================
# The algorithm works as follows:
# 1. Start with all packages in the "pending" set
# 2. Compute "installable" set: packages whose deps are ALL satisfied by
#    already-installed packages (or virtual provides of installed packages)
#    AND no conflicts with already-installed packages
# 3. Among installable packages, pick the one with:
#    a. LOWEST tier number (highest priority)
#    b. If tie: HIGHEST version (using epoch comparison)
#    c. If still tie: ALPHABETICALLY FIRST name
# 4. Install it (add to installed set)
# 5. Repeat until all packages installed or deadlock
#
# CRITICAL: Some packages will be EXCLUDED because of conflicts.
# If a package conflicts with an already-installed package, it is SKIPPED permanently.
# The final answer is the ordered list of successfully installed packages.

def resolve_packages(packages):
    """Run the resolution algorithm and return the install order."""
    installed = []  # ordered list of installed package names
    installed_set = set()
    pending = set(packages.keys())
    skipped = set()

    # Build virtual provides lookup
    virtual_map = {}  # virtual_name -> set of packages that provide it
    for pkg, info in packages.items():
        for virt in info["provides"]:
            if virt not in virtual_map:
                virtual_map[virt] = set()
            virtual_map[virt].add(pkg)

    while pending:
        installable = []
        for pkg in sorted(pending):
            if pkg in skipped:
                continue
            info = packages[pkg]

            # Check conflicts with already installed
            has_conflict = False
            for conflict in info["conflicts"]:
                if conflict in installed_set:
                    has_conflict = True
                    break
            if has_conflict:
                skipped.add(pkg)
                continue

            # Check all dependencies satisfied
            deps_satisfied = True
            for dep_name, dep_op, dep_ver in info["depends"]:
                # Check if dep_name is directly installed
                if dep_name in installed_set:
                    # Check version constraint
                    if not version_satisfies(packages[dep_name]["version"], dep_op, dep_ver):
                        deps_satisfied = False
                        break
                # Check if dep_name is a virtual provide satisfied by installed pkg
                elif dep_name in virtual_map:
                    found = False
                    for provider in virtual_map[dep_name]:
                        if provider in installed_set:
                            # Virtual provides always satisfy version constraints
                            found = True
                            break
                    if not found:
                        deps_satisfied = False
                        break
                else:
                    deps_satisfied = False
                    break

            if deps_satisfied:
                installable.append(pkg)

        if not installable:
            break  # Deadlock or done

        # Sort: lowest tier, then highest version, then alphabetical
        def sort_key(pkg):
            info = packages[pkg]
            ver_tuple = parse_version(info["version"])
            # Negate version for descending sort
            neg_ver = tuple(-x for x in ver_tuple)
            return (info["tier"], neg_ver, pkg)

        installable.sort(key=sort_key)
        chosen = installable[0]

        installed.append(chosen)
        installed_set.add(chosen)
        pending.remove(chosen)

    return installed, list(skipped)

# Run the resolution
install_order, skipped_pkgs = resolve_packages(packages)

# ============================================================================
# WRITE DATA FILES
# ============================================================================

os.makedirs("/app/data", exist_ok=True)

# File 1: packages.db - Binary format with package metadata
# Format: 4-byte magic "PKDB", 4-byte count, then for each package:
#   2-byte name_len, name, 2-byte version_len, version, 1-byte tier, 4-byte installed_size
#   2-byte num_provides, [2-byte len, provide_name]*
with open("/app/data/packages.db", "wb") as f:
    f.write(b"PKDB")
    f.write(struct.pack("<I", len(packages)))
    for name in sorted(packages.keys()):
        info = packages[name]
        name_bytes = name.encode()
        ver_bytes = info["version"].encode()
        f.write(struct.pack("<H", len(name_bytes)))
        f.write(name_bytes)
        f.write(struct.pack("<H", len(ver_bytes)))
        f.write(ver_bytes)
        f.write(struct.pack("<B", info["tier"]))
        f.write(struct.pack("<I", info["installed_size"]))
        f.write(struct.pack("<H", len(info["provides"])))
        for prov in info["provides"]:
            prov_bytes = prov.encode()
            f.write(struct.pack("<H", len(prov_bytes)))
            f.write(prov_bytes)

# File 2: dependencies.txt - Human-readable but with tricky formatting
# Format: "pkg_name: dep_name (op version), dep_name (op version), ..."
# But some lines have trailing comments that change meaning!
with open("/app/data/dependencies.txt", "w") as f:
    f.write("# Package Dependency Database v3.2.1\n")
    f.write("# Format: package: dependency (operator version), ...\n")
    f.write("# Note: virtual packages are resolved through provides declarations\n")
    f.write("#\n")
    for name in sorted(packages.keys()):
        info = packages[name]
        if info["depends"]:
            deps_str = ", ".join(f"{d} ({op} {v})" for d, op, v in info["depends"])
            f.write(f"{name}: {deps_str}\n")
        else:
            f.write(f"{name}: (none)\n")

# File 3: conflicts.conf - INI-style conflict declarations
with open("/app/data/conflicts.conf", "w") as f:
    f.write("[conflicts]\n")
    f.write("# Packages listed on same line cannot coexist\n")
    f.write("# Resolution: first installed wins, later conflicting packages are skipped\n")
    f.write("#\n")
    written_conflicts = set()
    for name in sorted(packages.keys()):
        for conflict in packages[name]["conflicts"]:
            pair = tuple(sorted([name, conflict]))
            if pair not in written_conflicts:
                f.write(f"{pair[0]} <-> {pair[1]}\n")
                written_conflicts.add(pair)

# File 4: resolver.conf - The resolution algorithm specification
with open("/app/data/resolver.conf", "w") as f:
    f.write("""[resolver]
# Package Resolution Algorithm v3.2.1
# 
# The resolver installs packages iteratively:
# 1. Identify all packages whose dependencies are fully satisfied
#    by the set of already-installed packages.
# 2. Among candidates, exclude any that conflict with installed packages.
#    Conflicting packages are permanently skipped.
# 3. Select the next package to install using this priority:
#    a. Lowest tier number (tier 1 = most critical, tier 5 = optional)
#    b. On tier tie: highest version wins (IMPORTANT: epoch-aware comparison!)
#    c. On version tie: alphabetically first package name wins
# 4. Install the selected package and repeat from step 1.
# 5. Continue until no more packages can be installed.
#
# VERSION COMPARISON:
# Versions may have an epoch prefix: "epoch:major.minor.patch"
# If no epoch is specified, epoch defaults to 0.
# Epochs are compared FIRST - a higher epoch ALWAYS wins regardless of
# the major.minor.patch numbers. Example: "2:0.1.0" > "1:99.99.99"
#
# VIRTUAL PROVIDES:
# A dependency on "virtual-X" is satisfied if ANY installed package
# declares "provides: virtual-X" in the package database.
# Virtual provides always satisfy version constraints (version is not checked
# for virtual resolution).
#
# OUTPUT:
# The install order is the sequence of package names, one per line.
# Skipped packages (due to conflicts) should NOT appear in the output.

algorithm_version = 3
epoch_aware = true
virtual_resolution = true
conflict_mode = first_wins
""")

# File 5: Write the reference answer
os.makedirs("/var/lib/tbench", exist_ok=True)
reference = {
    "install_order": install_order,
    "skipped": sorted(skipped_pkgs),
    "total_installed": len(install_order),
    "total_skipped": len(skipped_pkgs),
}

with open("/var/lib/tbench/.reference.json", "w") as f:
    json.dump(reference, f, indent=2)

# Print summary
print(f"Generated package database with {len(packages)} packages")
print(f"Install order: {len(install_order)} packages")
print(f"Skipped (conflicts): {len(skipped_pkgs)} packages: {sorted(skipped_pkgs)}")
print(f"Reference written to /var/lib/tbench/.reference.json")
