from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-t11-latememo/main.cpp').read_text()
a='''            std::array<u64, 3> moved{}, breaks{};
            const bool use_screen = screened_eval;
            screened_eval = false;
            auto next = use_screen ? anchor_screen.next : initial_next;'''
assert s.count(a)==1
s=s.replace(a,'''            const bool use_screen = screened_eval;
            screened_eval = false;
            // A successful commuting screen already proved the final display.
            // With late/no memo, links would only repeat the cap test below.
            // Keep the cap check on the exact replayed order, before using its cost.
            if(!use_screen || (cfg.memo && !cfg.late_memo)
#ifdef SCREEN_LINK_CHECK
               || true
#endif
            ) {
            std::array<u64,3> moved{},breaks{};
            auto next = use_screen ? anchor_screen.next : initial_next;''')
a='''            auto& path = path_buffer;
            path.clear();''';assert s.count(a)==1;s=s.replace(a,'            }\n'+a)
for name,source,extra in [('dcomp-t11-linkless',s,''),('dcomp-t11-linkless-check','#define SCREEN_REPLAY_CHECK 1\n'+s,'検証版は可換screenの計画を元の可視性再生で全件照合する。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-latememo\n\n可換anchorのscreenで完成表示が正しいと分かり、end-memoが後段または無効の時は、評価前半の193byteリンク配列二本のコピー・更新を省く。その配列が担っていたcap順序条件は、既存の可視性再生後の完全なordで同じく検査する。screenの対象外と古いmemo経路は元の実装を使う。'+extra+'\n\n浮動小数点計算、合法性、候補順・予算を保つ。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
