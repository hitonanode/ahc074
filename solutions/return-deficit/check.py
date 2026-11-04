from itertools import combinations
from pathlib import Path
import json
count=0
for n in range(11):
 for pairs in range(n+1):
  singles=n-pairs
  exact=min(sum(i*(2 if i in places else 1)for i in range(n))for places in combinations(range(n),pairs))
  formula=pairs*(pairs-1)+singles*pairs+singles*(singles-1)/2
  assert exact==formula,(singles,pairs,exact,formula)
  count+=1
print({'verified_count_profiles':count,'maximum_papers':10})
