from pathlib import Path
root=Path(__file__).resolve().parents[2];base=(root/'solutions/dcomp-combo-ten/main.cpp').read_text()
def make(name,s,desc):
 p=root/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: solutions/dcomp-combo-ten\n\n'+desc+'\n\n探索・予算・浮動小数点の加算順は変更しない。ログ・実験スイッチ・DesignStoreを保持し、時間fallbackは使わない。\n')
a=base.index('    void canonicalize() {');b=base.index('    struct State {',a);part=base[a:b]
part=part.replace('        bool gen_seen = false;\n','        // cur=-1 encodes that a generic sheet has already been seen.\n')
part=part.replace('if (k < M) gen_seen = true;', 'if (k < M) cur = -1;').replace('!gen_seen && c <= cur','c <= cur').replace('gen_seen ? 0 : std::min(cur, c)','std::max(cur, 0)')
assert 'gen_seen' not in part
make('dcomp-canon-min',base[:a]+part+base[b:],'canonicalizeの下からの走査で、汎用紙を見た状態をcur=-1で表す。列に残る条件はc<=curの1個となる。外れる紙は必ずc>curなので、levelのmin(cur,c)を省き、max(cur,0)で同じ値を作る。')
# A single AVX2 scan obtains both indices instead of two libc memchr calls.
s=base
needle='    // The paper at position p goes to position dest (the papers between shift by one).'
new='''    // Two distinct byte IDs, both present. Scan them together; negative anchor means top.
    __attribute__((target("avx2"))) static std::pair<int,int> find_edit(const ByteOrder& o,int k,int a) {
        if(a<0)return {find_paper(o,k),0};
        const auto vk=_mm256_set1_epi8(k),va=_mm256_set1_epi8(a);
        int p=-1,q=-1;
        for(int i=0;i<K;i+=32) {
            const auto v=_mm256_loadu_si256((const __m256i*)(o.data()+i));
            const unsigned km=_mm256_movemask_epi8(_mm256_cmpeq_epi8(v,vk));
            const unsigned am=_mm256_movemask_epi8(_mm256_cmpeq_epi8(v,va));
            if(km)p=i+__builtin_ctz(km);
            if(am)q=i+__builtin_ctz(am);
            if(p>=0 && q>=0)break;
        }
        return {p,q+1};
    }
'''
assert s.count(needle)==1;s=s.replace(needle,new+needle)
for space in ['                    ','                ']:
 old=space+'const int p = find_paper(ord, k);\n'+space+'int dest = a < 0 ? 0 : find_paper(ord, a) + 1;'
 if old in s:s=s.replace(old,space+'auto [p,dest] = find_edit(ord,k,a);')
old='                        const int p = find_paper(replay_order, x);\n                        int dest = a < 0 ? 0 : find_paper(replay_order, a) + 1;'
assert s.count(old)==1;s=s.replace(old,'                        auto [p,dest] = find_edit(replay_order,x,a);')
make('dcomp-find-two',s,'後処理の可視性再生で、移動する紙とanchorの位置をAVX2の同じ走査で求める。別々のmemchrで同じ192枚を調べる負担を減らす。負のanchorは従来のtop挿入。')
