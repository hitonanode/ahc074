from pathlib import Path
p=Path('solutions/argon-req-newfull-liftfirst'); assert not p.exists(); p.mkdir()
s=Path('solutions/argon-req-newfull-fast/main.cpp').read_text()
a='''        const bool ready = prepare_joint(u, opt, {}, hh);
        const auto prefix = save();'''
b='''        const bool ready = prepare_joint(u, opt, {}, hh);
        if (ready) {
            const int d = ded[u];
            if (is_filler(d)) { drop_filler(d); move_to_target_top(d); top_d = d; }
            else lift(d);
        }
        const auto prefix = save();'''
assert s.count(a)==1;s=s.replace(a,b,1)
a='''                if (ready) finish_joint_tail(u, {cd}, hh);'''
b='''                if (ready) {
                    u64 remaining = hh;
                    place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, remaining);
                    if (!invalid) fix_handles(u, remaining);
                }'''
assert s.count(a)==1;s=s.replace(a,b,1)
# The full reference is used for every feasible trial; avoid computing the old
# handle-only reference in that extra option unless the full reference failed.
a='''        const double completed_reference = opt.complete_value ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;
        const double returned_reference = opt.full_old ? joint_local_value(u, opt, {}) : 1e30;'''
b='''        const double returned_reference = opt.full_old ? joint_local_value(u, opt, {}) : 1e30;
        const double completed_reference = opt.complete_value && returned_reference >= 1e29
            ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;'''
assert s.count(a)==1;s=s.replace(a,b,1)
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

完成計画を使う新しいフィラーの共同DP重みの追加案。旧紙の全返却、汎用層編集、要求紙Dの持ち上げまでを共通に実行して保存し、各フィラーの取り出しと残るハンドル修正だけを反復する。新しい候補がDの列の掘り出し先に与える影響は重み付け時には近似するが、選ばれた計画は元のpre/post順で実行し、正当性と最終plan_costで選ぶ。既存の候補、旧紙の重み、探索予算は変更しない。

old_full_calls/invalidは局所完成評価の数と無効数、old_full_plans/better/gainは追加計画の有効数、初期最良値の更新数・改善量。すべての既存ログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、節と目次は保持する。
''')
print(p)
