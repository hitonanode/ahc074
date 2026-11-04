"""Assemble the standalone eight-sheet candidate from the recorded base and exact table."""
from itertools import permutations, product
from pathlib import Path
import re

D=Path(__file__).resolve().parent
root=D.parents[1]
source=(root/'solutions/as6-canon/main.cpp').read_text()
seven=(root/'solutions/astra-decoder/seven.cpp').read_text()
rows=[line.split() for line in (D/'poset8.txt').read_text().splitlines()[1:]]
costs={int(r,16):int(c) for r,c in rows}
assert len(costs)==16999

def canonical(r):
    out=[r>>(8*a)&255 for a in range(8)]
    ins=[sum((out[b]>>a&1)<<b for b in range(8)) for a in range(8)]
    keys=[(out[a].bit_count(),ins[a].bit_count()) for a in range(8)]
    groups=[[a for a in range(8) if keys[a]==key] for key in sorted(set(keys))]
    options=[]
    for group in groups:
        variants=[]
        for order in permutations(group):
            # Keep one order of vertices with identical predecessor/successor sets.
            if any(out[order[i]]==out[order[j]] and ins[order[i]]==ins[order[j]] and order[i]>order[j]
                   for i in range(len(order)) for j in range(i+1,len(order))):continue
            variants.append(order)
        options.append(variants)
    best=(1<<64)-1
    for blocks in product(*options):
        order=sum(blocks,())
        value=sum(((out[order[i]]>>order[j])&1)<<(8*i+j) for i in range(8) for j in range(8))
        best=min(best,value)
    return best

alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-'
def varint(value):
    out=''
    while True:
        value,bits=divmod(value,32)
        out+=alphabet[bits+(32 if value else 0)]
        if not value:return out

packed='';previous=0
for relation, cost in costs.items():
    trans=sum(((relation>>(8*i+j))&1)<<(8*j+i) for i in range(8) for j in range(8))
    both=cost+costs[canonical(trans)]
    packed+=varint(relation-previous)+varint(both)
    previous=relation

gen=(D/'generate.cpp').read_text()
canonical_cpp=gen[gen.index('U canonical('):gen.index('\nstruct Graph')]
canonical_cpp=canonical_cpp.replace('U canonical(U r,int n)', 'u64 canonical8(u64 r)').replace('    unsigned out[8]', '    constexpr int n=8;\n    unsigned out[8]')
canonical_cpp=re.sub(r'\bU\b','u64',canonical_cpp)
transpose=source[source.index('u64 transpose8('):source.index('struct PosetSums')]
extra=transpose+canonical_cpp+'\nconstexpr char kPoset8Packed[] =\n'
extra+='\n'.join('"'+packed[i:i+120]+'"' for i in range(0,len(packed),120))+';\n'
extra+=r'''
// Each packed entry is the difference of sorted canonical relations followed by
// the sum of exact legal distances for that relation and its transpose. The table
// contains every eight-element partial order, independently of the input targets.
struct Poset8Costs {
    static constexpr unsigned CS=1u<<20;
    std::vector<u64> keys,relations;
    std::vector<int> values,both;
    long long misses=0;
    static unsigned hash(u64 r){r^=r>>27;r*=0x3c79ac492ba7b653ULL;r^=r>>33;return unsigned(r)&(CS-1);}
    Poset8Costs():keys(CS,~0ULL),values(CS){
        const char* p=kPoset8Packed;
        auto read=[&](){
            u64 value=0;unsigned shift=0;
            for(;;){
                unsigned char c=*p++;
                unsigned digit=c>='0'&&c<='9'?c-'0':c>='A'&&c<='Z'?c-'A'+10:c>='a'&&c<='z'?c-'a'+36:c=='_'?62:63;
                value|=u64(digit&31)<<shift;
                if(!(digit&32))return value;
                shift+=5;
            }
        };
        u64 relation=0;
        for(int i=0;i<16999;++i){relation+=read();relations.push_back(relation);both.push_back(int(read()));}
        assert(!*p);
    }
    int cost(u64 raw){
        unsigned h=hash(raw);if(keys[h]==raw)return values[h];
        int value=0;
        if(!(raw&transpose8(raw))){
            u64 closed=closure8(raw,8);
            if(!(closed&kDiagonal)){
                ++misses;u64 canonical=canonical8(closed);
                auto it=std::lower_bound(relations.begin(),relations.end(),canonical);
                assert(it!=relations.end()&&*it==canonical);
                value=1+both[it-relations.begin()];
            }
        }
        keys[h]=raw;values[h]=value;return value;
    }
    static Poset8Costs&get(){static Poset8Costs table;return table;}
};
struct WindowStats{int iterations=0;double score=0,gobj_before=0,gobj_after=0;int climb_steps=0;};
'''
assignment=seven[seven.index('WindowStats assign_windows(std::vector<u64>& A,int m,int g,'):seven.index('// kBitLanes')]
assignment=assignment.replace('Poset7Costs','Poset8Costs').replace('poset7_cache_misses','poset8_cache_misses')
for a,b in [('7','8'),('21','28'),('72','73'),('50400','403200'),('25200','201600'),('2016','16128')]:
    assignment=re.sub(r'\b'+a+r'\b',b,assignment)
assignment=assignment.replace('const bool sparse = env_int("SPARSE_WINDOWS") > 0;', 'constexpr bool sparse = false;')
start=source.index('// The sums of the 720 legal distances')
end=source.index('// kBitLanes')
source=source[:start]+extra+assignment+source[end:]
source=source.replace('#include <array>','#include <array>\n#include <bit>')
source=source.replace('kCapWindow = 63, kCapPaper = 6','kCapWindow = 63, kCapPaper = 8')
source=source.replace('int M = 6, G = 38, H = 25;', 'int M = 8, G = 40, H = 23;')
source=source.replace('int M = 6, G = 38;  // as6-cap38: 38 generic windows',
                      'int M = 8, G = env_int("EIGHT_G") ? env_int("EIGHT_G") : 40;')
source=source.replace('return PosetSums::get().both_of(r) / 1440.0;',
                      'return (Poset8Costs::get().cost(r) - 1) / 80640.0;')
source=source.replace('if (attempt >= 2 || (!untimed && elapsed_sec() > kInitGiveUp)) return emergency_design(originalA, R);\n        G = attempt == 0 ? 32 : 28;',
                      'std::cerr << "design_failed = 1\\n"; return 0;')
source=source.replace('return emergency_design(originalA, R);','return 0;')
start=source.index('// Emergency design (no design found in time)')
end=source.index('}  // namespace',start)
source=source[:start]+source[end:]
# Keep model analysis separate from ordinary interactive execution. Fixed iteration
# flags are already present in the base, with the same constant PRNG seeds.
needle='    // Papers: six generic sheets, the cap, then the columns'
assert needle in source
source=source.replace(needle,'    if (env_int("MODEL_ONLY")) return 0;\n\n'+needle)
source='// Eight-sheet comparison code; exact offline table, no six-sheet fallback. See README.md.\n'+source[source.index('#include <algorithm>'):]
(D/'main.cpp').write_text(source)
print('packed bytes',len(packed),'standalone bytes',len(source))
