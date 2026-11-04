from pathlib import Path
from itertools import permutations
from collections import deque
import json
p=Path(__file__).resolve().parent
perms=list(permutations(range(5)));index={v:i for i,v in enumerate(perms)};edges=[(a,b)for a in range(5)for b in range(a+1,5)]
def close(r):
 row=[(r>>(8*a))&31 for a in range(5)]
 for k in range(5):
  for a in range(5):
   if row[a]>>k&1:row[a]|=row[k]
 return sum(v<<(8*a)for a,v in enumerate(row))
def rename(r,order):
 result=0
 while r:
  x=(r&-r).bit_length()-1;r&=r-1;result|=1<<(8*order[x//8]+order[x%8])
 return result
forward={close(sum(1<<(8*a+b)for e,(a,b)in enumerate(edges)if mask>>e&1))for mask in range(1024)}
labels={rename(r,order)for r in forward for order in perms};assert len(labels)==4231
nexts=[]
for order in perms:
 dst=[]
 for at in range(4):
  for depth in range(5):
   if at==depth:continue
   q=list(order);x=q.pop(at);q.insert(depth,x);dst.append(index[tuple(q)])
 nexts.append(dst)
distance=[]
for start in range(120):
 dist=[255]*120;dist[start]=0;q=deque([start])
 while q:
  a=q.popleft()
  for b in nexts[a]:
   if dist[b]==255:dist[b]=dist[a]+1;q.append(b)
 assert max(dist)<=4;distance.append(dist)
orders=[sum(1<<(8*o[a]+o[b])for a in range(5)for b in range(a+1,5))for o in perms]
remaining=set(labels);classes=[]
while remaining:
 r=min(remaining);goals=[i for i,o in enumerate(orders)if not r&~o];assert goals
 total=sum(min(d[g]for g in goals)for d in distance)
 orbit={rename(r,o)for o in perms};remaining-=orbit;classes.append((r,total*6))
assert len(classes)==63
(p/'classes.json').write_text(json.dumps(classes,indent=2)+'\n')
s=(p.parent/'tight-thirty-eight'/'main.cpp').read_text()
a=s.index('constexpr PosetClass kPosetClasses[');b=s.index('\n};',a)+3
s=s[:a]+'constexpr PosetClass kPosetClasses[63] = {\n'+''.join(f'    {{0x{r:x}ULL, {cost}}},\n'for r,cost in classes)+'};'+s[b:]
s=s.replace('static constexpr unsigned kSize = 1U << 18;','static constexpr unsigned kSize = 1U << 14;')
s=s.replace('std::array<int, 6> p{0, 1, 2, 3, 4, 5};','std::array<int, 5> p{0, 1, 2, 3, 4};')
s=s.replace('for (int a = 0, e = 0; a < 6; ++a)','for (int a = 0, e = 0; a < 5; ++a)').replace('for (int b = a + 1; b < 6; ++b, ++e)','for (int b = a + 1; b < 5; ++b, ++e)')
s=s.replace('if (m != 6 || g >= 64','if (m != 5 || g >= 64').replace('kCapPaper = 6;','kCapPaper = 5;').replace('static constexpr int GM = 6;','static constexpr int GM = 5;')
s=s.replace('int M = 6, G = 38, H = 25;','int M = 5, G = 34, H = 29;').replace('int M = 6, G = 38;','int M = 5, G = 34;')
s=s.replace('for(int k=7;k<K;k++)','for(int k=kCapPaper+1;k<K;k++)').replace('for(int y=7;y<K;y++)','for(int y=kCapPaper+1;y<K;y++)')
s=s.replace('six-sheet comparator','five-sheet comparator').replace('G=38 generic windows and H=25 handles','G=34 generic windows and H=29 handles').replace('six generic sheets','five generic sheets').replace('All 15 pairs occur, giving 720 distinct orders','All 10 pairs occur, giving 120 distinct orders').replace('185 product papers: 71 serve a pair of products and 114 serve one','186 product papers: 70 serve a pair of products and 116 serve one')
s=s.replace('kPosetClasses lists one closed relation of each of the 318 unlabeled','kPosetClasses lists one closed relation of each of the 63 unlabeled').replace('partial orders of 6 elements','partial orders of 5 elements').replace('to the 130023 labeled ones','to the 4231 labeled ones')
s=s.replace('// The sums of the 720 legal distances','// Six times the sums of the 120 legal distances')
# The assignment screen also packs comparison pairs independently of WindowRelations.
# Its old 15-pair extraction cannot be used for a five-sheet comparator.
import re
for begin in ['            uint32_t forward = _pext_u64(c, ', '            const uint32_t forward = _pext_u64(c,0x']:
 a=s.index(begin);b=s.index('\n',s.index('uint32_t reverse = _pext_u64',a))+1
 s=s[:a]+'''            uint32_t forward = 0, reverse = 0;
            for (int x=0,e=0;x<5;x++) for(int y=x+1;y<5;y++,e++) {
                forward |= uint32_t(c >> (8*y+x) & 1) << e;
                reverse |= uint32_t(c >> (8*x+y) & 1) << e;
            }
'''+s[b:]
a=s.index('    auto make_transfer_options =');b=s.index('    auto apply_move =',a) if '    auto apply_move =' in s[a:] else s.index('    for (int p = 0; p < np; p++)',a)
part=s[a:b]
part=re.sub(r'\b15\b','10',part)
part=part.replace('(1U << 30)-1','(1U << 20)-1').replace('(1U<<30)-1','(1U<<20)-1')
s=s[:a]+part+s[b:]
s=s.replace('relation of 6 sheets','relation of 5 sheets').replace('orders of the 6 generic','orders of the 5 generic').replace('Needs m = 6','Needs m = 5')
(p/'main.cpp').write_text(s)
print({'closed_relations':len(labels),'classes':len(classes),'states':120,'source_bytes':len(s.encode())})
