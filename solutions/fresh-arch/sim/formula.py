# staircase cost model: column sizes s_c (c=1 top..C bottom), random target uniform over papers
# dig = (s_c-1)/2 , holes = C-c ; cost = dig + f*holes ; optimize integer sizes by greedy marginal
import math
def best(Kp, C, f):
    s=[1]*C
    def marg(i):  # cost increase of adding one paper to column i (0-based, top=0)
        n=s[i]
        # total cost contribution sum over papers in col: n*(n-1)/2 + f*(C-1-i)*n
        return ( (n+1)*n/2 - n*(n-1)/2 ) + f*(C-1-i)
    for _ in range(Kp-C):
        i=min(range(C), key=marg); s[i]+=1
    tot=sum(n*(n-1)/2 + f*(C-1-i)*n for i,n in enumerate(s))
    dig=sum(n*(n-1)/2 for n in s)/Kp; hol=sum((C-1-i)*n for i,n in enumerate(s))/Kp
    return tot/Kp, dig, hol, s
for f in [0.5,0.39,0.3,0.2,0.1]:
    res=min((best(192,C,f)+(C,) for C in range(5,60)), key=lambda r:r[0])
    print(f"f={f}: C={res[4]} cost={res[0]:.2f} dig={res[1]:.2f} holes={res[2]:.2f} sizes={res[3]}")
