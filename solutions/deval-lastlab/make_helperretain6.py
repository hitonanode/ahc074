from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
a='''        const auto olds = fillers;
        return_visible_fillers(olds, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;'''
b='''        const auto olds = fillers;
        FillerList retired;
        GenericSplit old_split;split_generic(old_split);
        bool all_visible=true;for(const auto& f:olds)all_visible&=visible(f.paper);
        for(const auto& f:olds) {
            const u64 shown=shown_by(f);
            // Keep an already-correct filler only when the remaining returns are
            // visible and it cannot hide the requested column. Generic sheets stay contiguous.
            const bool keep=all_visible && old_split.below(f.paper) &&
                !(shown & (1ULL<<handle[col_of[d]])) &&
                !((paper[f.paper].black^A[u]) & shown & ~paper[d].opaque);
            if(!keep)retired.push_back(f);
        }
        return_visible_fillers(retired, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''    void finish_handles(int u, int d, u64 hh) {
        for (auto& pk : choose_fillers_dp(u, d, hh)) {'''
b='''    void finish_handles(int u, int d, u64 hh) {
        for(const auto& f:fillers)hh&=~shown_by(f);
        for (auto& pk : choose_fillers_dp(u, d, hh)) {'''
assert s.count(a)==1;s=s.replace(a,b)
a='''        for (const auto& h : interleave->helpers[u]) {
            const int dep = helper_depth[h.paper];'''
b='''        for (const auto& h : interleave->helpers[u]) {
            if(is_filler(h.paper))continue;
            const int dep = helper_depth[h.paper];'''
assert s.count(a)==1;s=s.replace(a,b)
p=root/'solutions/deval-helper-retain';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-helpeq1`。

helper計画を作る前に、旧fillerを全て返す制約を緩める。旧fillerが全て見えていて、対象の列を隠さず、genericより下で今回の要求色を満たしているfillerは、その場に残す。その他だけを従来の可視順で返す。残したfillerの表示範囲は追加filler・handle fixの必要範囲から除き、残した紙自身は新規helper候補から外す。候補数は同じで追加の計画列挙はしない。全計画は既存の表示・可視性・fillers_reachable検査とplan_costを通す。他の設計・固定予算・ログと実験スイッチを保ち、時計では切り替えない。
''');print(len(s.encode()))
