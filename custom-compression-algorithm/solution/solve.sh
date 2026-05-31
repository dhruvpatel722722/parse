#!/bin/bash
# Oracle solution: derives records from records.dat via known-plaintext cryptanalysis.
# Approach: Use XOR-difference analysis to determine block permutation and XOR key,
# then verify using the hash=sha256(data+seq)[:8] relationship in each record.
mkdir -p /app/output

cat > /app/recover.py << 'PYEOF'
import struct, json, os, hashlib, itertools, re
os.makedirs("/app/output", exist_ok=True)

FRAME = 128; N = 200; BS = 8; NB = 16
with open("/app/data/records.dat", "rb") as f:
    data = f.read()
frames = [data[i*FRAME:(i+1)*FRAME] for i in range(N)]

# Character sets from the format specification
KEY = set(range(ord('a'),ord('z')+1))|{ord('.')}|set(range(ord('0'),ord('9')+1))|{0}
HEX = set(range(ord('0'),ord('9')+1))|set(range(ord('a'),ord('f')+1))
DIG = set(range(ord('0'),ord('9')+1))

# Find constant and varying destination blocks
const_d = [d for d in range(NB) if all(frames[i][d*BS:(d+1)*BS]==frames[0][d*BS:(d+1)*BS] for i in range(1,N))]
vary_d = [d for d in range(NB) if d not in const_d]

# Find ID block (src 0): XOR-diff bytes 0-3 = LE uint32(i)
did = None
for d in vary_d:
    s=d*BS
    if all(bytes(frames[i][s+j]^frames[0][s+j] for j in range(4))==struct.pack('<I',i) for i in range(1,N)):
        did=d; break

# Heuristic source identification via zero-diff patterns
rem = [d for d in vary_d if d!=did]
def zd(d):
    s=d*BS
    return frozenset(j for j in range(BS) if all(frames[i][s+j]==frames[0][s+j] for i in range(1,N)))

pa = {did:0}
zds = {d:zd(d) for d in rem}
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

def recover(fp, s4d):
    """Try to recover all records with given perm and src4 location."""
    K=bytearray(FRAME)
    for d in const_d: K[d*BS:(d+1)*BS]=frames[0][d*BS:(d+1)*BS]
    if s4d is not None:
        s=s4d*BS; K[s+4]^=100; K[s+5]^=97; K[s+6]^=116; K[s+7]^=97
    K[did*BS:did*BS+4]=frames[0][did*BS:did*BS+4]
    
    inv={fp[d]:d for d in range(NB) if fp[d]>=0}
    
    # Recover K for each varying byte using appropriate charset
    for d in vary_d:
        src=fp[d]
        if src<0: continue
        for j in range(BS):
            if d==did and j<4: continue
            p=d*BS+j
            if all(frames[i][p]==frames[0][p] for i in range(1,N)): continue
            # Choose charset based on source
            if src in (1,2): cs=KEY
            elif src==5: cs={61} if j==0 else HEX
            elif src==6: cs=HEX
            elif src==7: cs={44} if j==1 else ({32} if j==2 else ({115} if j==3 else ({101} if j==4 else ({113} if j==5 else ({61} if j==6 else DIG)))))
            elif src==8: cs=DIG if j<3 else (DIG|{44} if j==3 else {32,44,104,97,115,61})
            elif src==9: cs={115,104} if j==0 else ({61,104} if j==1 else (HEX|{61}))
            elif src==10: cs=HEX|{0}
            elif src==0: cs=KEY-{0} if j>=4 else set(range(256))
            else: continue
            cands=[k for k in range(256) if all((frames[i][p]^k) in cs for i in range(N))]
            if not cands: return None
            K[p]=cands[0]
    
    # Correlation fix for src 8 bytes 3-7
    if 8 in inv:
        d8=inv[8]
        for k3 in range(256):
            if not all((frames[i][d8*BS+3]^k3) in (DIG|{44}) for i in range(N)): continue
            b3=[frames[i][d8*BS+3]^k3 for i in range(N)]
            e4=[44 if v in DIG else 32 for v in b3]; k4=set(frames[i][d8*BS+4]^e4[i] for i in range(N))
            if len(k4)!=1: continue
            e5=[32 if v in DIG else 104 for v in b3]; k5=set(frames[i][d8*BS+5]^e5[i] for i in range(N))
            if len(k5)!=1: continue
            e6=[104 if v in DIG else 97 for v in b3]; k6=set(frames[i][d8*BS+6]^e6[i] for i in range(N))
            if len(k6)!=1: continue
            e7=[97 if v in DIG else 115 for v in b3]; k7=set(frames[i][d8*BS+7]^e7[i] for i in range(N))
            if len(k7)!=1: continue
            K[d8*BS+3]=k3; K[d8*BS+4]=k4.pop(); K[d8*BS+5]=k5.pop(); K[d8*BS+6]=k6.pop(); K[d8*BS+7]=k7.pop()
            break
    
    # Correlation fix for src 9 bytes 0-1
    if 9 in inv:
        d9=inv[9]
        for k0 in range(256):
            if not all((frames[i][d9*BS]^k0) in {115,104} for i in range(N)): continue
            b0=[frames[i][d9*BS]^k0 for i in range(N)]
            e1=[104 if v==115 else 61 for v in b0]; k1=set(frames[i][d9*BS+1]^e1[i] for i in range(N))
            if len(k1)==1: K[d9*BS]=k0; K[d9*BS+1]=k1.pop(); break
    
    # Hash-based digit resolution
    dp=[]
    if 7 in inv:
        p=inv[7]*BS+7; c=[k for k in range(256) if all((frames[i][p]^k) in DIG for i in range(N))]
        if len(c)>1: dp.append((p,c))
    if 8 in inv:
        for j in range(3):
            p=inv[8]*BS+j; c=[k for k in range(256) if all((frames[i][p]^k) in DIG for i in range(N))]
            if len(c)>1: dp.append((p,c))
    
    null=b'\x00'
    for combo in (itertools.product(*[c for _,c in dp]) if dp else [()]):
        Kt=bytearray(K)
        for idx,(p,_) in enumerate(dp): Kt[p]=combo[idx]
        S=bytes(frames[0][p]^Kt[p] for p in range(FRAME))
        P=bytearray(FRAME)
        for d in range(NB):
            src=fp[d]
            if src>=0: P[src*BS:(src+1)*BS]=S[d*BS:(d+1)*BS]
        if struct.unpack('<I',P[0:4])[0]!=0: continue
        key=P[4:36].split(null)[0].decode('ascii',errors='replace')
        pts=key.split('.')
        if len(pts)!=3 or not pts[0].isalpha() or not pts[0].islower(): continue
        if not pts[1].isalpha() or not pts[1].islower(): continue
        if not pts[2].isdigit() or len(pts[2])!=3: continue
        val=P[36:128].split(null)[0].decode('ascii',errors='replace')
        m=re.match(r'^data=([0-9a-f]{16}), seq=(\d+), hash=([0-9a-f]{8})$',val)
        if not m: continue
        dh,ss,hv=m.groups()
        if hashlib.sha256((dh+ss).encode()).hexdigest()[:8]!=hv: continue
        # Decode all
        recs=[]
        ok=True
        for i in range(N):
            Si=bytes(frames[i][p]^Kt[p] for p in range(FRAME))
            Pi=bytearray(FRAME)
            for d in range(NB):
                src=fp[d]
                if src>=0: Pi[src*BS:(src+1)*BS]=Si[d*BS:(d+1)*BS]
            if struct.unpack('<I',Pi[0:4])[0]!=i: ok=False; break
            recs.append({"id":i,"key":Pi[4:36].split(null)[0].decode('ascii'),"value":Pi[36:128].split(null)[0].decode('ascii')})
        if ok: return recs
    return None

found=None
for asn in itertools.permutations(ua_s):
    fp=[-1]*NB; fp[did]=0
    for d,s in pa.items(): fp[d]=s
    for i,d in enumerate(ua): fp[d]=asn[i]
    for s4 in const_d:
        r=recover(fp,s4)
        if r: found=r; break
    if found: break

assert found, "Recovery failed"
found.sort(key=lambda r:r["id"])
with open("/app/output/recovered.json","w") as f:
    json.dump(found,f,indent=2)
print(f"Recovered {N} records")
PYEOF

python3 /app/recover.py
