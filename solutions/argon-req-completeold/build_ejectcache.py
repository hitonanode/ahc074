from pathlib import Path
r=Path('solutions');s=(r/'argon-req-completeeject/main.cpp').read_text()
a=s.index('        // The value-weighted joint plan can lose before ejection.')
b=s.index('        post_secondary_saved += original_length',a)
block=s[a:b]
s=s[:a]+s[b:]
block=block.replace('            const auto& c = cached->edited;\n            const double value', '''            const auto& c = cached->edited;
            if (cached->complete || c.state.order == order) continue;
            const double value''')
block=block.replace('if (!cached->complete && c.state.order != order && c.cost <= value + .5 &&','if (c.cost <= value + .5 &&')
block=block.replace('                ++value_seed_trials;','                F3_DIAG(f3_stage = 3; f3_round = 0;)\n                ++value_seed_trials;')
block=block.replace('                    ++value_seed_accepts;','                    winning_operator = 4; winning_round = 0; winning_escape = false;\n                    ++value_seed_accepts;')
# The heavy trace must describe the actual final path, including the added pass.
point='            if (chosen_path != baseline_path) {'
assert s.count(point)==1
s=s.replace(point,''.join('    '+line if line.strip() else line for line in block.splitlines(True))+point)
s=s.replace('                weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});','                if (cache_plans) weighted_raw.push_back({cost, save(), ops OP_TAG(, op_tags)});')
p=r/'argon-req-ejectcache';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-completefast-v3

2種類の状態価値付き共同DPの計画が、通常の候補編集後に負けてejectを受けない場合を補う。既存のplan_cacheにある編集済み結果を使い、完成した最良結果と積層が異なり、評価値差が0.5以内の候補だけに既存のpolish_ejectsを適用する。通常の勝者として既にejectを受けた候補と、同じ編集済み積層の重複は処理しない。完成したplan_costを厳密に改善した場合だけ採用する。

候補のDPや編集は解き直さず、中立探索の追加実行もしない。除外できる候補はplan_costを計算する前に省く。追加処理は重いトレースの出力前に行い、#heavyにも実際の最終操作列を残す。

既存の設計、目的関数、探索予算、乱数は変更しない。将来の注文を参照しない。ログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@ops、段の目印と目次を維持する。新しい環境変数はない。既存の候補キャッシュが有効な設定でだけ働く。

追加stderr指標: value_seed_trials（追加eject数）、value_seed_valid（有効数）、value_seed_accepts（採用数）、value_seed_gain（完成評価値の改善合計）、value_seed_saved（採用時の即時手数差）。gain/savedは、その後の注文も含む実現スコア差とは区別する。F3_PROFILEでは既存の追加計画段、heavy traceではplans.directとして記録する。
''')
