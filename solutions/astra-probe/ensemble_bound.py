"""Analytic generator-ensemble lower bound, with double-precision evaluation.
All combinatorial counts are exact integers; only log/exp evaluation is rounded.
"""
import json
import math

M=math.comb(64,32)
near=0
mean_distance=0.0
for d in range(32):
    if d:near+=math.comb(32,d)**2
    remaining=M-1-near
    tail=0.0 if remaining<255 else math.exp(sum(math.log1p(-near/(M-1-j)) for j in range(255)))
    mean_distance+=2*tail
p_mid=sum(math.comb(32,d)**2*(math.comb(2*d,d)-2) for d in range(1,33))/((M-1)*(M-2))
mean_triples=3*math.comb(256,3)*p_mid
mean_g=3*mean_triples/256
one_upper=65-mean_distance+mean_g
per_transition=2-one_upper/255
per_query=(1023*per_transition+255/256)/1024
print(json.dumps(dict(weight32_words=M,mean_nearest_distance=mean_distance,
                     midpoint_probability=p_mid,mean_triples=mean_triples,
                     mean_triple_incidence=mean_g,mean_one_step_upper_uncapped=one_upper,
                     expected_lower_after_first=per_transition,
                     expected_lower_all_1024=per_query,
                     expected_score_lower=per_query*1024),indent=2))
