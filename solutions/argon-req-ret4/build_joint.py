from pathlib import Path
s=Path('solutions/argon-req-ret4/main.cpp').read_text()
s=s.replace('''        const int l = col_of[d];
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        auto fix = fix_costs(u, hh);''','''        const bool keep_previous = opt.ret_mode == 4;
        if (keep_previous && !can_keep_previous(u)) { invalid = true; return; }
        const u64 previous_cover = keep_previous ? paper[top_d].opaque : 0;
        const int l = col_of[d];
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask & ~previous_cover;
        auto fix = fix_costs(u, hh);''',1)
s=s.replace('''        if (x0 >= 0) add_old(x0, -1, -1, true);''','''        if (x0 >= 0 && !keep_previous) add_old(x0, -1, -1, true);''',1)
s=s.replace('''        if (x0 >= 0) {
            if (x0_lvl >= 0) {''','''        if (x0 >= 0) {
            if (keep_previous) {
                top_d = -1;
                fillers.push_back({x0, 0, col_of[x0]});
            } else if (x0_lvl >= 0) {''',1)
s=s.replace('''        set_generic(u, hole_all);''','''        set_generic(u, hole_all & ~previous_cover);''',1)
s=s.replace('''            for (int fm : fms) {
                start_plan(st0);
                ++r1_trials;''','''            auto keep_fms = fms;
            keep_fms.push_back(5);
            for (int fm : keep_fms) {
                start_plan(st0);
                ++r1_trials;''',1)
Path('solutions/argon-req-ret4-joint/main.cpp').write_text(s)
Path('solutions/argon-req-ret4-joint/README.md').write_text('''改良元: solutions/esw-slim

R1の色付き据え置き候補を、既存の新旧フィラー同時選択DP（run_joint）にも組み込む。前の商品紙の色が今回の商品紙の全ての穴で正しいことを確認し、その紙が覆う汎用窓とハンドル窓を残作業から除く。前の商品紙は据え置きに固定し、それ以外の新旧フィラーを同時に選択する。

通常の色付き据え置き候補（旧フィラー返却／再利用）の2系統も残す。旧ret_mode=4では許されなかった、正しい色の汎用穴を覆う場合だけ追加する。ARGON_R1_NEW_ONLY=1。r1_*の指標はargon-req-ret4と同じで、追加試行にはjointも含む。ARGON_R1_PROBEは測定用。全ての既存ログ・スイッチ・プロファイラ・予算・DesignStoreは維持し、設計と評価関数は変えない。
''')
