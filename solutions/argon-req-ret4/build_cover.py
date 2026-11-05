from pathlib import Path
for name,base in [('argon-req-cover','esw-slim'),('argon-req-cover-keep','argon-req-ret4')]:
 s=Path('solutions',base,'main.cpp').read_text()
 s=s.replace('''    void set_generic(int u, u64 holes) {''','''    long long r1_coverage_calls = 0, r1_coverage_windows = 0, r1_coverage_complete = 0;
    void set_generic(int u, u64 holes) {''',1)
 s=s.replace('''        int offset = -1;
        for (int i = 0; i < K; i++) {
            if (order[i] < M) {
                offset = i;
                break;
            }
        }
        if (offset < 0 || offset + M > K) {''','''        int offset = -1;
        u64 covered = 0, correct = 0;
        for (int i = 0; i < K; i++) {
            const int k = order[i];
            if (k < M) {
                offset = i;
                break;
            }
            // These papers remain above the generic layer through the rest of the plan.
            // Only the first opaque paper is visible at each hole of the requested product.
            const u64 shown = holes & paper[k].opaque & ~covered;
            correct |= shown & ~(paper[k].black ^ A[u]);
            covered |= shown;
        }
        if (correct) {
            ++r1_coverage_calls;
            r1_coverage_windows += __builtin_popcountll(correct);
            holes &= ~correct;
            if (!holes) { ++r1_coverage_complete; return; }
        }
        if (offset < 0 || offset + M > K) {''',1)
 s=s.replace('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "r1_coverage_calls = " << solver.r1_coverage_calls
              << "\\nr1_coverage_windows = " << solver.r1_coverage_windows
              << "\\nr1_coverage_complete = " << solver.r1_coverage_complete << '\\n';
''',1)
 p=Path('solutions',name)
 p.joinpath('main.cpp').write_text(s)
 p.joinpath('README.md').write_text('''改良元: solutions/esw-slim

R1の発展案。set_genericで比較層より上に残る紙の実際の表示色を前から順に調べ、今回の商品紙の汎用穴を正しく覆う部分を並べ替え対象から除く。run_jointと通常計画の共通箇所で処理する。比較層より下の紙は除外判定に使わない。同じ窓を複数枚が覆う場合は最初の不透明紙だけを評価する。

既存の設計・予算・評価関数・全スイッチ・ログ・プロファイラ・DesignStoreは維持する。新しいr1_coverage_calls/windows/completeは、計画シミュレーション中に穴を除いた呼出し数・窓数・全ての汎用穴が覆われた回数。実際に選ばれた注文だけの数ではない。
'''+('''
この版はargon-req-ret4の色付き汎用窓による据え置き候補も追加する（ARGON_R1_NEW_ONLY=1）。r1_*の据え置き指標も継承する。
''' if base!='esw-slim' else ''))
