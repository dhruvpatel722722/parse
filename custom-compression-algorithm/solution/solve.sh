#!/bin/bash
# Oracle solution: recovers records from records.dat using known-plaintext cryptanalysis.
# The approach uses XOR-difference analysis, charset constraints, cross-byte correlation,
# and SHA-256 hash verification to fully determine the encoding parameters.
mkdir -p /app/output

cat > /app/recover.py << 'PYEOF'
import struct, json, os, hashlib, itertools, re
import sys

os.makedirs("/app/output", exist_ok=True)

FRAME = 128; N = 200; BS = 8; NB = 16
with open("/app/data/records.dat", "rb") as f:
    raw = f.read()
frames = [raw[i*FRAME:(i+1)*FRAME] for i in range(N)]

# Precompute encrypted values per position
EV = [[frames[i][p] for i in range(N)] for p in range(FRAME)]
DV = [set(EV[p]) for p in range(FRAME)]

# Character sets
KEY = set(range(97,123)) | {46} | set(range(48,58)) | {0}
HEX = set(range(48,58)) | set(range(97,103))
DIG = set(range(48,58))

def valid_k(p, cs):
    """Find all K values where every frame's decoded byte is in charset cs."""
    result = set(range(256))
    for v in DV[p]:
        result &= {v^c for c in cs}
        if not result: return []
    return sorted(result)

# Step 1: Classify blocks
const_d = [d for d in range(NB) if all(len(DV[d*BS+j])==1 for j in range(BS))]
vary_d = [d for d in range(NB) if d not in const_d]

# Step 2: Find ID block
did = None
for d in vary_d:
    s = d*BS
    ok = True
    for i in range(1, min(N, 10)):  # check first 10 for speed
        for j in range(4):
            if (frames[i][s+j] ^ frames[0][s+j]) != (struct.pack('<I',i)[j]):
                ok = False; break
        if not ok: break
    if ok:
        # Full verify
        if all(bytes(frames[i][s+j]^frames[0][s+j] for j in range(4)) == struct.pack('<I',i) for i in range(1,N)):
            did = d; break

# Step 3: Assign sources via zero-diff
rem = [d for d in vary_d if d != did]
zds = {}
for d in rem:
    zds[d] = frozenset(j for j in range(BS) if len(DV[d*BS+j])==1)
pa = {did: 0}
for d in rem:
    if len(zds[d])>=4 and frozenset(range(4,8))<=zds[d]: pa[d]=10; break
for d in rem:
    if d in pa: continue
    if len(zds[d])>=5 and frozenset(range(1,6))<=zds[d]: pa[d]=7; break
for d in rem:
    if d in pa: continue
    if zds[d]==frozenset({0}): pa[d]=5; break
for d in rem:
    if d in pa: continue
    if 7 in zds[d] and len(zds[d])<=3: pa[d]=2; break
ua = [d for d in rem if d not in pa]
ua_s = sorted({1,2,5,6,7,8,9,10}-set(pa.values()))

# Step 4: For each permutation candidate, try full recovery
def try_perm(fp, s4d):
    K = bytearray(FRAME)
    # Constant blocks
    for d in const_d:
        for j in range(BS): K[d*BS+j] = frames[0][d*BS+j]
    if s4d is not None:
        s=s4d*BS; K[s+4]^=100; K[s+5]^=97; K[s+6]^=116; K[s+7]^=97
    K[did*BS:did*BS+4] = frames[0][did*BS:did*BS+4]
    
    inv = {fp[d]:d for d in range(NB) if fp[d]>=0}
    
    # For each varying position, get charset and find K candidates
    # Use tight per-position charsets based on actual value format
    ambig = []  # positions with multiple candidates
    for d in vary_d:
        src = fp[d]
        if src < 0: continue
        for j in range(BS):
            if d==did and j<4: continue
            p = d*BS+j
            if len(DV[p])==1: continue  # constant, already set
            cs = _cs(src, j)
            if cs is None: continue
            cands = valid_k(p, cs)
            if not cands: return None
            K[p] = cands[0]
            if len(cands) > 1: ambig.append((p, cands, src, j))
    
    # Correlation for src 8 bytes 3-7
    if 8 in inv:
        d8 = inv[8]
        ok8 = False
        for k3 in valid_k(d8*BS+3, DIG|{44}):
            b3 = [EV[d8*BS+3][i]^k3 for i in range(N)]
            pairs = [(44,32),(32,104),(104,97),(97,115)]
            chain = [k3]
            good = True
            for off, (if_dig, if_comma) in enumerate(pairs, 4):
                exp = [if_dig if v in DIG else if_comma for v in b3]
                ks = set(EV[d8*BS+off][i]^exp[i] for i in range(N))
                if len(ks)!=1: good=False; break
                chain.append(ks.pop())
            if good:
                for off, kv in enumerate(chain): K[d8*BS+3+off] = kv
                ok8 = True; break
        if not ok8: return None
    
    # Fix K for constant non-zero plaintext positions in varying blocks
    # src 5 byte 0: always '=' (61)
    if 5 in inv:
        p = inv[5]*BS+0
        if len(DV[p]) == 1: K[p] = frames[0][p] ^ 61
    # src 7 bytes 1-6: always ", seq=" = [44,32,115,101,113,61]
    if 7 in inv:
        known7 = [None, 44, 32, 115, 101, 113, 61, None]
        for j in range(1, 7):
            p = inv[7]*BS+j
            if len(DV[p]) == 1: K[p] = frames[0][p] ^ known7[j]
    # src 8 bytes 4-7 handled by correlation above
    # src 9 bytes 0-1 handled by correlation below
    # src 4 (constant block) handled by s4d XOR above
    
    # Correlation for src 9 bytes 0-1
    if 9 in inv:
        d9 = inv[9]
        ok9 = False
        for k0 in valid_k(d9*BS, frozenset({115,104})):
            b0 = [EV[d9*BS][i]^k0 for i in range(N)]
            exp1 = [104 if v==115 else 61 for v in b0]
            k1s = set(EV[d9*BS+1][i]^exp1[i] for i in range(N))
            if len(k1s)==1:
                K[d9*BS]=k0; K[d9*BS+1]=k1s.pop(); ok9=True; break
        if not ok9: return None
    
    # Digit resolution via hash
    dp = []
    if 7 in inv:
        p=inv[7]*BS+7; c=valid_k(p, DIG)
        if len(c)>1: dp.append((p,c))
    if 8 in inv:
        for j in range(3):
            p=inv[8]*BS+j; c=valid_k(p, DIG)
            if len(c)>1: dp.append((p,c))
    
    # Also handle KEY ambiguity: for key blocks, positions with few distinct values
    # have multiple candidates. We resolve by trying combos and checking key format.
    key_ambig = [(p,c) for p,c,src,j in ambig if src in (0,1,2) and len(c)<=4]
    
    null = b'\x00'
    pat = re.compile(r'^data=([0-9a-f]{16}), seq=(\d+), hash=([0-9a-f]{8})$')
    key_pat = re.compile(r'^[a-z]+\.[a-z]+\.\d{3}$')
    
    all_ambig = key_ambig + dp
    if not all_ambig:
        all_ambig = [None]  # dummy for single pass
    
    for combo in (itertools.product(*[c for _,c in all_ambig]) if all_ambig and all_ambig[0] is not None else [()]):
        Kt = bytearray(K)
        if all_ambig and all_ambig[0] is not None:
            for idx,(p,_) in enumerate(all_ambig):
                Kt[p] = combo[idx]
        # Decode frame 0
        P = bytearray(FRAME)
        for d in range(NB):
            src = fp[d]
            if src>=0:
                for j in range(BS): P[src*BS+j] = EV[d*BS+j][0] ^ Kt[d*BS+j]
        if struct.unpack('<I',P[0:4])[0] != 0: continue
        key = P[4:36].split(null)[0].decode('ascii', errors='replace')
        if not key_pat.match(key): continue
        val = P[36:128].split(null)[0].decode('ascii', errors='replace')
        m = pat.match(val)
        if not m: continue
        dh,ss,hv = m.groups()
        if hashlib.sha256((dh+ss).encode()).hexdigest()[:8] != hv: continue
        # Full decode
        recs = []
        ok = True
        for i in range(N):
            Pi = bytearray(FRAME)
            for d in range(NB):
                src = fp[d]
                if src>=0:
                    for j in range(BS): Pi[src*BS+j] = EV[d*BS+j][i] ^ Kt[d*BS+j]
            if struct.unpack('<I',Pi[0:4])[0] != i: ok=False; break
            recs.append({"id":i, "key":Pi[4:36].split(null)[0].decode('ascii'),
                        "value":Pi[36:128].split(null)[0].decode('ascii')})
        if ok: return recs
    return None

def _cs(src, j):
    if src in (1,2): return KEY
    if src==0: return (KEY-{0}) if j>=4 else None
    if src==5: return frozenset({61}) if j==0 else HEX
    if src==6: return HEX
    if src==7: return [HEX,{44},{32},{115},{101},{113},{61},DIG][j]
    if src==8: return DIG if j<3 else (DIG|{44} if j==3 else {32,44,104,97,115,61})
    if src==9: return {115,104} if j==0 else ({61,104} if j==1 else (HEX|{61}))
    if src==10: return HEX|{0}
    return None

# Main search
found = None
for asn in itertools.permutations(ua_s):
    fp = [-1]*NB; fp[did]=0
    for d,s in pa.items(): fp[d]=s
    for i,d in enumerate(ua): fp[d]=asn[i]
    for s4 in const_d:
        r = try_perm(fp, s4)
        if r: found=r; break
    if found: break

assert found, "Recovery failed"
found.sort(key=lambda r:r["id"])
with open("/app/output/recovered.json","w") as f:
    json.dump(found, f, indent=2)
print(f"Recovered {N} records")
PYEOF

python3 /app/recover.py
