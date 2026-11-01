"""Exhaustive sanity check of the mover-count lemma for N <= 12.
Compositions are visible-window counts of successive visible papers.
This is not a proof of attainability of the resulting product-count bound.
"""
def compositions(n):
    if not n:
        yield []
    else:
        for first in range(1,n+1):
            for rest in compositions(n-first):
                yield [first]+rest

for n in range(1,13):
    for delta in range(1,n+1):
        best=0
        for weights in compositions(n):
            prefix=count=0
            for a in weights:
                count += prefix >= delta or a >= delta
                prefix += a
            best=max(best,count)
            assert count <= n-delta+1,(n,delta,weights,count)
        assert best==n-delta+1
print('Verified all compositions of N=1..12, delta=1..N: maximum eligible movers = N-delta+1.')
