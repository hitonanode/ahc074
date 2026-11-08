from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100]);s=s.replace(a,b)
sub('    void prepare_post_context(const State& initial) {','    void prepare_post_context(const State& initial, int u) {')
sub('        prepare_post_context(initial);','        prepare_post_context(initial,u);')
sub('            c.blocks[0][j] = {paper[k].opaque, paper[k].black};','''            // On a valid mask, the first wrong color composes like the first color.
            // Cache it for this request so trial filters need no repeated XOR/view sum.
            c.blocks[0][j] = {paper[k].opaque, c.masks_exact ?
                (paper[k].black ^ A[u]) & paper[k].opaque : paper[k].black};''')
a=s.index('                u64 seen = 0, view = 0;\n                if (!use_screen) {');b=s.index('                if (cfg.memo) {',a)
old=s[a:b]
loopstart=old.index('                for (int k = next[root]; k != root;) {')
loopend=old.index('                if (view != A[u]) return false;')
loop=old[loopstart:loopend]
x='''                    if ((disp ^ A[u]) & cov & ~seen) return false;
                    view |= disp & ~seen;'''
y='''                    if constexpr (WrongMasks) {
                        if(disp & ~seen)return false;
                    } else {
                        if ((disp ^ A[u]) & cov & ~seen) return false;
                        view |= disp & ~seen;
                    }'''
assert loop.count(x)==1;loop=loop.replace(x,y)
new='''                if (!use_screen) {
                    auto matches=[&]<bool WrongMasks>() {
                        u64 seen=0,view=0;
'''+loop+'''                        if constexpr(WrongMasks)return !(A[u]&~seen);
                        else return view==A[u];
                    };
                    const bool matched=post_context.masks_exact ? matches.template operator()<true>() : matches.template operator()<false>();
#ifdef BAD_FILTER_CHECK
                    if(post_context.masks_exact) {
                        u64 covered=0,shown=0;
                        for(int k=next[root];k!=root;k=next[k]) {
                            shown|=paper[k].black&~covered;covered|=paper[k].opaque;
                            if(covered==~u64(0))break;
                        }
                        if(matched!=(shown==A[u]))std::abort();
                    }
#endif
                    if(!matched)return false;
                }
'''
s=s[:a]+new+s[b:]
for name,extra in [('dcomp-filter-bad',''),('dcomp-filter-bad-check','#define BAD_FILTER_CHECK 1\n')]:
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(extra+s)
 (p/'README.md').write_text('''改良元: solutions/dcomp-screen-replay

注文ごとのpost_contextの区間表には、最初の色の代わりに「要求と違う最初の色」のmaskを保存する。正しい不透明maskなら、区間の結合演算は同じで、試行の表示検査は新しく見えるwrong bitの有無だけを調べればよい。表示全体の再構成と毎回のXORを省く。まだ覆われない窓の要求bitも最後に確認する。blackがopaque外に出る実験状態は元の表と検査を使う。

BAD_FILTER_CHECKは紙を全部たどった表示と試行ごとに一致を検査する。探索と浮動小数点の採否は不変。予算、ログ、実験スイッチ、DesignStoreを維持し、時間fallbackなし。
''')
