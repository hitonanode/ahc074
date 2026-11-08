from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
def make(name,s,desc):
 d=S/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s);(d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\n'+desc+'\n\n予算は両コンパイラ共通の固定値。時計での軽量化なし。既存ログ・trace・profiler・switch・段と目次・DesignStoreを保持する。\n')
x='''                    note(path OP_TAG(, tags), value);
                    const bool won = value < incumbent_value - 1e-9;'''
assert b.count(x)==1
make('dcomp-t12-expanded-seed',b.replace(x,'''                    note(path OP_TAG(, tags), value);
                    neutral_seeds.push_back({value,save(),path OP_TAG(,tags)});
                    const bool won = value < incumbent_value - 1e-9;'''),'すでに通常の拡張候補探索で最後まで修復した計画も、追加親の選択肢に入れる。追加親は従来どおり費用差0.3以内から1個、1→1候補を1個、主親と6枠共有。追加の完成計画作成はしない。')
x='''                if(round==1) {
                    int second_count=0;''';assert b.count(x)==1
make('dcomp-t12-pool-seed',b.replace(x,'''                if(round==1) {
                    // Reuse legal edited plans already retained for the final near-tie choice.
                    for(const auto& c:tie_pool) {
                        bool seen=false;
                        for(const auto& old:neutral_seeds)seen|=old.state.order==c.state.order;
                        if(!seen)neutral_seeds.push_back({c.value,c.state,c.path OP_TAG(,c.tags)});
                    }
                    int second_count=0;'''),'最終near-tie選択用にすでに保存した合法な編集済み計画も、追加親の候補に入れる。ALTと同じ最終紙順は足さない。追加親1個・1→1・主親と6枠共有の予算は変えない。')
s=b
x='// ==== Window assignment: annealing and climb (assign_windows) ===='
s=s.replace(x,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC push_options\n#pragma GCC optimize("align-loops=32","align-jumps=16","align-functions=64")\n#endif\n'+x)
x='// ==== Design: units, columns and the cost model ===='
s=s.replace(x,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC pop_options\n#endif\n'+x)
make('dcomp-t12-mapalign',s,'GCCで窓割当の関数・loopの配置を明示して命令境界の影響を測る。窓割当関数本体のサイズはalt1/dual25で同じだが64byte内の開始位置が異なるため、この仮説を一度検証する。Clangは元のコンパイル設定を維持する。計算・乱数・探索量は同じ。')
