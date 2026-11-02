# Pair statistics for random targets: Hamming distance distribution, and expected number of pairs
# servable by "region toggles" (k regions, each with a complementary helper pair B_i/~B_i):
# pair (u,v) servable iff on every region, u's colors on D∩R_i equal B_i or ~B_i  (prob 2^{k-|D|} for random B)
import itertools, collections
def load(seed):
    L=open(f"/home/sato/ahc074/tools/in/{seed:04d}.txt").read().split()
    A=[int(s[::-1],2) for s in L[4:4+256]]
    return A
for seed in [0,1]:
    A=load(seed)
    cnt=collections.Counter()
    for i in range(256):
        for j in range(i+1,256):
            cnt[bin(A[i]^A[j]).count('1')]+=1
    print("seed",seed,"min dist",min(cnt),"pairs with d<=16,18,20,22,24:",[sum(c for d,c in cnt.items() if d<=t) for t in (16,18,20,22,24)])
    for k in (1,2,3,4,6,8):
        print("  k=%d expected servable pairs (random B): %.1f"%(k,sum(c*2.0**(k-d) for d,c in cnt.items())))
