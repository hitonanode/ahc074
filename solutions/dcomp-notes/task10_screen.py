from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-combo-ten/main.cpp').read_text()
def sub(a,b):
    global s
    assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b)
sub('    struct AnchorScreen {\n        bool active = false;', '    struct AnchorScreen {\n        Links next, prev;  // final G before the commuting re-anchor\n        bool active = false;')
sub('        auto evaluate = [&](const std::vector<Edit>& trial) {','''        // Only a successful, exact anchor screen may supply the final links.
        // Consume this flag at entry so later deletion/ejection trials cannot reuse it.
        bool screened_eval = false;
        int screened_anchor = -1;
        auto evaluate = [&](const std::vector<Edit>& trial) {''')
sub('            auto next = initial_next, prev = initial_prev;\n            {\n                CF_SCOPE(eval_filter);','''            const bool use_screen = screened_eval;
            screened_eval = false;
            auto next = use_screen ? anchor_screen.next : initial_next;
            auto prev = use_screen ? anchor_screen.prev : initial_prev;
            if (use_screen) splice_after(next, prev, anchor_screen.k, screened_anchor < 0 ? root : screened_anchor);
#ifdef SCREEN_LINK_CHECK
            if (use_screen) {
                auto nx = initial_next, pv = initial_prev;
                for (const auto& e : trial) splice_after(nx,pv,e.paper,e.anchor<0?root:e.anchor);
                if (nx!=next || pv!=prev) std::abort();
            }
#endif
            {
                CF_SCOPE(eval_filter);''')
sub('                for (const Edit& e : trial) {\n                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;', '                if (!use_screen) for (const Edit& e : trial) {\n                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;')
sub('                u64 seen = 0, view = 0;\n                for (int k = next[root]; k != root;) {','''                u64 seen = 0, view = 0;
                if (!use_screen) {
                for (int k = next[root]; k != root;) {''')
sub('                if (view != A[u]) return false;\n                if (cfg.memo) {','''                if (view != A[u]) return false;
                }
                if (cfg.memo) {''')
sub('            u64 cov = 0, disp = 0;\n            for (int x = nx[root]; x != root; x = nx[x]) {','''            S.next = nx;
            S.prev = pv;
            u64 cov = 0, disp = 0;
            for (int x = nx[root]; x != root; x = nx[x]) {''')
sub('        auto screen_rejects = [&](int a) {\n            const auto& S = screen;','''        auto screen_rejects = [&](int a) {
            screened_eval = false;
            const auto& S = screen;''')
sub('            const bool reject = shown != A[u];\n            screen_skipped += reject;','''            const bool reject = shown != A[u];
            screened_eval = !reject;
            screened_anchor = a;
            screen_skipped += reject;''')
for name,extra in [('dcomp-screen-links',''),('dcomp-screen-check','#define SCREEN_LINK_CHECK 1\n#define SCREEN_CHECK 1\n')]:
    p=root/'solutions'/name;assert not p.exists();p.mkdir()
    (p/'main.cpp').write_text(extra+s)
    (p/'README.md').write_text('''改良元: solutions/dcomp-combo-ten

付け替えの表示screenで既に作った最終リンクを、表示が正しいと証明できた試行のevaluateに渡す。後続の手と可換な場合だけ、Gのリンクから1回のspliceで試行の最終状態が得られる。元のcap不変条件、途中の可視性再生、canonicalizeと費用計算は保持する。消去・ejectなど他の試行に情報が漏れないようフラグはevaluateの入口で消費する。

乱数、予算、探索順、採否の浮動小数点演算は不変。SCREEN_LINK_CHECKは元のリンク再生との完全一致をabortで検証する。SCREEN_CHECKは元の表示との一致を集計する。時間によるfallbackはない。
''')
p=root/'solutions/dcomp-combo-profile';assert not p.exists();p.mkdir()
(p/'main.cpp').write_text('#define COLFAST_PROFILE 1\n'+(root/'solutions/dcomp-combo-ten/main.cpp').read_text())
(p/'README.md').write_text('改良元: solutions/dcomp-combo-ten\n\nCOLFAST_PROFILE=1で現在のM1注文処理を計測する。探索・採否は不変。時計は既存scaled時計を用いる。計測用で提出候補ではない。\n')
