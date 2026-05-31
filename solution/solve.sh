#!/bin/bash
cat > /app/solver.py << 'PYTHON'
import struct
import os

def parse_version(v):
    """Parse version string into comparable tuple (epoch, major, minor, patch)."""
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
    """Check if installed_ver satisfies the version constraint."""
    cmp = version_compare(installed_ver, constraint_ver)
    if constraint_op == ">=": return cmp >= 0
    if constraint_op == "<=": return cmp <= 0
    if constraint_op == ">": return cmp > 0
    if constraint_op == "<": return cmp < 0
    if constraint_op == "==": return cmp == 0
    if constraint_op == "!=": return cmp != 0
    return False

def read_packages_db(path):
    """Read the binary package database."""
    packages = {}
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"PKDB", f"Bad magic: {magic}"
        count = struct.unpack("<I", f.read(4))[0]
        for _ in range(count):
            name_len = struct.unpack("<H", f.read(2))[0]
            name = f.read(name_len).decode()
            ver_len = struct.unpack("<H", f.read(2))[0]
            version = f.read(ver_len).decode()
            tier = struct.unpack("<B", f.read(1))[0]
            size = struct.unpack("<I", f.read(4))[0]
            num_provides = struct.unpack("<H", f.read(2))[0]
            provides = []
            for _ in range(num_provides):
                prov_len = struct.unpack("<H", f.read(2))[0]
                provides.append(f.read(prov_len).decode())
            packages[name] = {
                "version": version,
                "tier": tier,
                "installed_size": size,
                "provides": provides,
                "depends": [],
                "conflicts": [],
            }
    return packages

def read_dependencies(path, packages):
    """Read dependencies.txt and populate package dependencies."""
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ": " not in line:
                continue
            pkg_name, deps_str = line.split(": ", 1)
            if deps_str == "(none)":
                continue
            if pkg_name not in packages:
                continue
            # Parse deps: "dep1 (>= ver1), dep2 (>= ver2), ..."
            deps = []
            for dep_part in deps_str.split("), "):
                dep_part = dep_part.strip().rstrip(")")
                if " (" in dep_part:
                    dep_name, constraint = dep_part.split(" (", 1)
                    parts = constraint.split()
                    if len(parts) >= 2:
                        op = parts[0]
                        ver = parts[1]
                        deps.append((dep_name.strip(), op, ver))
                else:
                    deps.append((dep_part.strip(), ">=", "0.0.0"))
            packages[pkg_name]["depends"] = deps

def read_conflicts(path, packages):
    """Read conflicts.conf and populate package conflicts."""
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if " <-> " in line:
                parts = line.split(" <-> ")
                if len(parts) == 2:
                    pkg1 = parts[0].strip()
                    pkg2 = parts[1].strip()
                    if pkg1 in packages:
                        packages[pkg1]["conflicts"].append(pkg2)
                    if pkg2 in packages:
                        packages[pkg2]["conflicts"].append(pkg1)

def resolve(packages):
    """Run the package resolution algorithm."""
    # Build virtual provides map
    virtual_map = {}  # virtual_name -> set of provider packages
    for pkg_name, info in packages.items():
        for virt in info["provides"]:
            if virt not in virtual_map:
                virtual_map[virt] = set()
            virtual_map[virt].add(pkg_name)

    installed = []
    installed_set = set()
    pending = set(packages.keys())
    skipped = set()

    while pending:
        installable = []
        for pkg in sorted(pending):
            if pkg in skipped:
                continue
            info = packages[pkg]

            # Check conflicts with already installed packages
            has_conflict = False
            for conflict in info["conflicts"]:
                if conflict in installed_set:
                    has_conflict = True
                    break
            if has_conflict:
                skipped.add(pkg)
                continue

            # Check all dependencies are satisfied
            deps_satisfied = True
            for dep_name, dep_op, dep_ver in info["depends"]:
                if dep_name in installed_set:
                    # Direct dependency - check version
                    if not version_satisfies(packages[dep_name]["version"], dep_op, dep_ver):
                        deps_satisfied = False
                        break
                elif dep_name in virtual_map:
                    # Virtual dependency - check if any provider is installed
                    found = False
                    for provider in virtual_map[dep_name]:
                        if provider in installed_set:
                            found = True
                            break
                    if not found:
                        deps_satisfied = False
                        break
                else:
                    # Dependency not available at all
                    deps_satisfied = False
                    break

            if deps_satisfied:
                installable.append(pkg)

        if not installable:
            break

        # Sort: lowest tier, then highest version (epoch-aware), then alphabetical
        def sort_key(pkg):
            info = packages[pkg]
            ver_tuple = parse_version(info["version"])
            neg_ver = tuple(-x for x in ver_tuple)
            return (info["tier"], neg_ver, pkg)

        installable.sort(key=sort_key)
        chosen = installable[0]

        installed.append(chosen)
        installed_set.add(chosen)
        pending.remove(chosen)

    return installed

def main():
    packages = read_packages_db("/app/data/packages.db")
    read_dependencies("/app/data/dependencies.txt", packages)
    read_conflicts("/app/data/conflicts.conf", packages)

    install_order = resolve(packages)

    os.makedirs("/app/output", exist_ok=True)
    with open("/app/output/install_order.txt", "w") as f:
        for pkg in install_order:
            f.write(pkg + "\n")

    print(f"Resolved {len(install_order)} packages")

if __name__ == "__main__":
    main()
PYTHON

python /app/solver.py
