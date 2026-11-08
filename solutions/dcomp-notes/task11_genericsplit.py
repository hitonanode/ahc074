from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='''        bool complete = false;
        bool below(int k) const { return complete && !above[k]; }''';assert B.count(a)==1
s=B.replace(a,'''        bool complete = false;
        double generic = 0;
        bool below(int k) const { return complete && !above[k]; }''')
a='''    void split_generic(GenericSplit& split) const {
        int count = 0;
        for (int i = 0; i < K && count < M; i++) {
            split.above[order[i]] = true;
            if (order[i] < M) count++;
        }
        split.complete = count == M;
    }''';assert s.count(a)==1
s=s.replace(a,'''    __attribute__((target("popcnt"))) void split_generic(GenericSplit& split) const {
        int count=0,rank=0;unsigned used=0;
        for(int i=0;i<K && count<M;++i) {
            const int k=order[i];split.above[k]=true;
            if(k<M) {
                rank=rank*(M-count)+__builtin_popcount(((1U<<k)-1)&~used);
                used|=1U<<k;++count;
            }
        }
        split.complete=count==M;
        split.generic=future.empty()?0.:0.5*future[rank];
#ifdef GENERIC_SPLIT_CHECK
        if(std::bit_cast<u64>(split.generic)!=std::bit_cast<u64>(generic_bias()))
            {std::cerr<<"GENERIC_SPLIT_MISMATCH\\n";std::abort();}
#endif
    }''')
for a,b in [('(kEndWeight * adaptive_next_cost(split) + generic_bias())','(kEndWeight * adaptive_next_cost(split) + split.generic)'),('memo->next_cost = kEndWeight * adaptive_next_cost(split) + generic_bias();','memo->next_cost = kEndWeight * adaptive_next_cost(split) + split.generic;'),('f[2] = generic_bias();','f[2] = split.generic;'),('baseline_next = kEndWeight * adaptive_next_cost(baseline_split) + generic_bias();','baseline_next = kEndWeight * adaptive_next_cost(baseline_split) + baseline_split.generic;')]:
 assert s.count(a)==1,a;s=s.replace(a,b)
for name,source,desc in [('dcomp-t11-generic-split',s,''),('dcomp-t11-generic-check','#define GENERIC_SPLIT_CHECK 1\n'+s,'元のgeneric_biasとのdouble全bit照合も毎回実行する検証版。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nplan_costがgeneric境界とgeneric permutation rankを別々に同じprefixを走査して求めていたため、一回の走査にまとめる。rankは元の整数漸化式・紙順を保ち、future表の同じ値を返す。'+desc+'\n\n要求の候補・計算の加算順・予算は変更しない。両コンパイラ共通。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
