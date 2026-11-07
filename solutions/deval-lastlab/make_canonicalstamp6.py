from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
a='    void canonicalize() {\n';assert s.count(a)==1;s=s.replace(a,'''    std::array<unsigned,K> canonical_stamp{};
    std::array<int,K> canonical_index{};
    unsigned canonical_epoch=0;
    void canonicalize() {
''')
a='''        std::array<int, K> nf_index;
        nf_index.fill(-1);'''
b='''        // Even stamps mark this pass; the low bit records an old filler.
        // Clearing the K-entry maps is needed only at unsigned wraparound.
        unsigned epoch=(canonical_epoch+=2);
        if(!epoch){canonical_stamp.fill(0);canonical_epoch=epoch=2;}
        auto& nf_index=canonical_index;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''            nf_index[nf[i].paper] = i;''';b=a+'\n            canonical_stamp[nf[i].paper]=epoch;';assert s.count(a)==1;s=s.replace(a,b)
a='''        std::array<bool, K> old_filler{};
        int res_count = 0;
        for (auto& f : fillers) {
            old_filler[f.paper] = true;
            if (nf_index[f.paper] >= 0) res[res_count++] = nf[nf_index[f.paper]];
        }
        for (int i = 0; i < nf_count; i++)
            if (!old_filler[nf[i].paper]) res[res_count++] = nf[i];'''
b='''        int res_count = 0;
        for(auto& f:fillers)if((canonical_stamp[f.paper]&~1U)==epoch) {
            res[res_count++]=nf[nf_index[f.paper]];
            canonical_stamp[f.paper]=epoch|1U;
        }
        for(int i=0;i<nf_count;++i)
            if(canonical_stamp[nf[i].paper]==epoch)res[res_count++]=nf[i];'''
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-canonicalstamp6';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-trim6b`。

canonicalizeのnf_index・old_filler全配列クリアを世代stampに変える。現在見つかったcolumn外紙だけindexとstampを書き、stampの下位bitで旧fillerの優先順に出力済みであることを記録する。旧記録に同一紙が重複していた場合も元の列挙順・重複数を保つ。unsigned世代が一周するときだけ全stampをクリアする。紙の走査、再構成結果、候補の受理順は同じ。ログ・統計・profiler・experiment switchと固定予算を保つ。
''');print(len(s.encode()))
