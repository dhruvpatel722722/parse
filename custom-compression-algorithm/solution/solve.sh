#!/bin/bash
# Oracle solution: recovers records from records.dat via known-plaintext attack.
mkdir -p /app/output

cat > /app/recover.py << 'PYEOF'
import struct, json, os, hashlib, re, itertools

os.makedirs("/app/output", exist_ok=True)
FRAME = 128; N = 200; BS = 8; NB = 16

with open("/app/data/records.dat", "rb") as f:
    raw = f.read()
frames = [raw[i*FRAME:(i+1)*FRAME] for i in range(N)]
EV = [[frames[i][p] for i in range(N)] for p in range(FRAME)]
DV = [set(ev) for ev in EV]

KEY_CHARS = set(range(97,123)) | {46} | set(range(48,58)) | {0}
HEX_CHARS = set(range(48,58)) | set(range(97,103))
DIGITS = set(range(48,58))
VOCAB = set(["alpha","beta","gamma","delta","epsilon","zeta","eta","theta","iota","kappa","lambda","mu","nu","xi","omicron","pi","rho","sigma","tau","upsilon","phi","chi","psi","omega","kernel","socket","buffer","cache","thread","mutex","queue","stack","heap","token","cipher","codec","proxy","router","bridge","driver","daemon","signal","packet","stream","vector","matrix","tensor","shader"])

def charset_for(src, j):
    if src in (1,2): return KEY_CHARS
    if src == 0: return None if j < 4 else (KEY_CHARS - {0})
    if src == 5: return frozenset({61}) if j == 0 else HEX_CHARS
    if src == 6: return HEX_CHARS
    if src == 7: return [HEX_CHARS, {44}, {32}, {115}, {101}, {113}, {61}, DIGITS][j]
    if src == 8:
        if j < 3: return DIGITS
        if j == 3: return DIGITS | {44}
        return {32, 44, 104, 97, 115, 61}
    if src == 9:
        if j == 0: return {115, 104}
        if j == 1: return {61, 104}
        return HEX_CHARS | {61}
    if src == 10: return HEX_CHARS | {0}
    return None

def vk(p, cs):
    r = set(range(256))
    for v in DV[p]:
        r &= {v ^ c for c in cs}
        if not r: return []
    return sorted(r)

# Classify blocks
const_d = [d for d in range(NB) if all(len(DV[d*BS+j]) == 1 for j in range(BS))]
vary_d = [d for d in range(NB) if d not in const_d]

# Find ID block
did = None
for d in vary_d:
    s = d * BS
    if all(bytes(EV[s+j][i] ^ EV[s+j][0] for j in range(4)) == struct.pack('<I', i) for i in range(1, N)):
        did = d; break

# Heuristic source assignment
rem = [d for d in vary_d if d != did]
zds = {d: frozenset(j for j in range(BS) if len(DV[d*BS+j]) == 1) for d in rem}
pa = {}
for d in rem:
    if len(zds[d]) >= 4 and frozenset(range(4,8)) <= zds[d]: pa[d] = 10; break
for d in rem:
    if d in pa: continue
    if len(zds[d]) >= 5 and frozenset(range(1,6)) <= zds[d]: pa[d] = 7; break
for d in rem:
    if d in pa: continue
    if zds[d] == frozenset({0}): pa[d] = 5; break
for d in rem:
    if d in pa: continue
    if 7 in zds[d] and len(zds[d]) <= 3: pa[d] = 2; break

ua = [d for d in rem if d not in pa]
ua_s = sorted({1,2,5,6,7,8,9,10} - set(pa.values()))

def try_recover(fp, s4d):
    inv = {fp[d]: d for d in range(NB) if fp[d] >= 0}
    K = bytearray(FRAME)
    # Constant blocks
    for d in const_d:
        for j in range(BS): K[d*BS+j] = frames[0][d*BS+j]
    if s4d is not None:
        s = s4d * BS
        K[s+4] ^= 100; K[s+5] ^= 97; K[s+6] ^= 116; K[s+7] ^= 97
    # ID block
    for j in range(4): K[did*BS+j] = frames[0][did*BS+j]
    # Fix constant non-zero positions
    resolved = set()
    if 5 in inv and len(DV[inv[5]*BS]) == 1:
        K[inv[5]*BS] = frames[0][inv[5]*BS] ^ 61; resolved.add(inv[5]*BS)
    if 7 in inv:
        kn7 = [None, 44, 32, 115, 101, 113, 61, None]
        for j in range(1, 7):
            p = inv[7]*BS+j
            if len(DV[p]) == 1: K[p] = frames[0][p] ^ kn7[j]; resolved.add(p)
    # Per-byte K recovery
    for d in vary_d:
        src = fp[d]
        if src < 0: continue
        for j in range(BS):
            if d == did and j < 4: continue
            p = d*BS+j
            if len(DV[p]) == 1:
                if p not in resolved: K[p] = frames[0][p]
                continue
            cs = charset_for(src, j)
            if cs is None: continue
            cands = vk(p, cs)
            if not cands: return None
            K[p] = cands[0]
    # Correlation src 8
    if 8 in inv:
        d8 = inv[8]
        for k3 in vk(d8*BS+3, DIGITS | {44}):
            b3 = [EV[d8*BS+3][i] ^ k3 for i in range(N)]
            pairs = [(44,32),(32,104),(104,97),(97,115)]; chain = [k3]; good = True
            for off, (a, b) in enumerate(pairs, 4):
                exp = [a if v in DIGITS else b for v in b3]
                ks = set(EV[d8*BS+off][i] ^ exp[i] for i in range(N))
                if len(ks) != 1: good = False; break
                chain.append(ks.pop())
            if good:
                for off, kv in enumerate(chain): K[d8*BS+3+off] = kv
                break
    # Correlation src 9
    if 9 in inv:
        d9 = inv[9]
        for k0 in vk(d9*BS, frozenset({115, 104})):
            b0 = [EV[d9*BS][i] ^ k0 for i in range(N)]
            exp1 = [104 if v == 115 else 61 for v in b0]
            k1s = set(EV[d9*BS+1][i] ^ exp1[i] for i in range(N))
            if len(k1s) == 1: K[d9*BS] = k0; K[d9*BS+1] = k1s.pop(); break
    # Ambiguous positions (not in resolved, not constant, multiple cands)
    ambig = []
    for d in vary_d:
        src = fp[d]
        if src < 0: continue
        for j in range(BS):
            if d == did and j < 4: continue
            p = d*BS+j
            if p in resolved: continue
            if len(DV[p]) == 1: continue
            cs = charset_for(src, j)
            if cs is None: continue
            cands = vk(p, cs)
            if len(cands) > 1: ambig.append((p, cands))
    total = 1
    for _, c in ambig: total *= len(c)
    if total > 200000: return None
    # Brute force with validation
    null = b'\x00'
    val_pat = re.compile(r'^data=([0-9a-f]{16}), seq=(\d+), hash=([0-9a-f]{8})$')
    key_pat = re.compile(r'^[a-z]+\.[a-z]+\.\d{3}$')
    for combo in (itertools.product(*[c for _, c in ambig]) if ambig else [()]):
        Kf = bytearray(K)
        for idx, (p, _) in enumerate(ambig): Kf[p] = combo[idx]
        P0 = bytearray(FRAME)
        for d in range(NB):
            src = fp[d]
            if src >= 0:
                for j in range(BS): P0[src*BS+j] = EV[d*BS+j][0] ^ Kf[d*BS+j]
            elif d == s4d:
                for j in range(BS): P0[4*BS+j] = EV[d*BS+j][0] ^ Kf[d*BS+j]
        if struct.unpack('<I', P0[0:4])[0] != 0: continue
        key0 = P0[4:36].split(null)[0].decode('ascii', errors='replace')
        if not key_pat.match(key0): continue
        parts = key0.split('.')
        if parts[0] not in VOCAB or parts[1] not in VOCAB: continue
        val0 = P0[36:128].split(null)[0].decode('ascii', errors='replace')
        m = val_pat.match(val0)
        if not m: continue
        dh, ss, hv = m.groups()
        if hashlib.sha256((dh + ss).encode()).hexdigest()[:8] != hv: continue
        
        # Also validate frame 1 to catch key-length edge cases
        P1 = bytearray(FRAME)
        for d in range(NB):
            src = fp[d]
            if src >= 0:
                for j in range(BS): P1[src*BS+j] = EV[d*BS+j][1] ^ Kf[d*BS+j]
            elif d == s4d:
                for j in range(BS): P1[4*BS+j] = EV[d*BS+j][1] ^ Kf[d*BS+j]
        if struct.unpack('<I', P1[0:4])[0] != 1: continue
        key1 = P1[4:36].split(null)[0].decode('ascii', errors='replace')
        if not key_pat.match(key1): continue
        pts1 = key1.split('.')
        if pts1[0] not in VOCAB or pts1[1] not in VOCAB: continue
        val1 = P1[36:128].split(null)[0].decode('ascii', errors='replace')
        m1 = val_pat.match(val1)
        if not m1: continue
        dh1, ss1, hv1 = m1.groups()
        if hashlib.sha256((dh1 + ss1).encode()).hexdigest()[:8] != hv1: continue
        # Full decode
        records = []
        ok = True
        for i in range(N):
            Pi = bytearray(FRAME)
            for d in range(NB):
                src = fp[d]
                if src >= 0:
                    for j in range(BS): Pi[src*BS+j] = EV[d*BS+j][i] ^ Kf[d*BS+j]
                elif d == s4d:
                    for j in range(BS): Pi[4*BS+j] = EV[d*BS+j][i] ^ Kf[d*BS+j]
            rid = struct.unpack('<I', Pi[0:4])[0]
            if rid != i: ok = False; break
            ki = Pi[4:36].split(null)[0].decode('ascii')
            if not key_pat.match(ki): ok = False; break
            vi = Pi[36:128].split(null)[0].decode('ascii')
            records.append({"id": rid, "key": ki, "value": vi})
        if ok: return records
    return None

# Search
found = None
for asn in itertools.permutations(ua_s):
    fp = [-1] * NB; fp[did] = 0
    for d, s in pa.items(): fp[d] = s
    for i, d in enumerate(ua): fp[d] = asn[i]
    for s4 in const_d:
        r = try_recover(fp, s4)
        if r: found = r; break
    if found: break

assert found, "Recovery failed"
found.sort(key=lambda r: r["id"])
with open("/app/output/recovered.json", "w") as f:
    json.dump(found, f, indent=2)
print(f"Successfully recovered {N} records")
PYEOF


python3 /app/recover.py
