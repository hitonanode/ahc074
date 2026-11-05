from pathlib import Path
r=Path('solutions');s=(r/'argon-req-ejectcache/main.cpp').read_text()
a=s.index('                    const auto incumbent = save();', s.index('            if (weighted_ready)'))
b=s.index('                }\n            }\n            if (chosen_path != baseline_path)',a)
body=s[a:b]
body=body.replace('                    winning_operator = 4; winning_round = 0; winning_escape = false;\n','')
body=body.replace('                        winning_operator = 4; winning_round = 0; winning_escape = false;\n','')
# Obtain a standalone body with the same state snapshots, calls and comparisons.
body='\n'.join(line[12:] if line.startswith('            ') else line for line in body.split('\n'))
body=body.replace('polish_ejects(st0, c.path, u OP_TAG(, tags), 4, true)', 'polish_ejects(initial, c.path, u OP_TAG(, tags), 4, true)')
body=body.replace('chosen_path', 'chosen').replace('best_tags','chosen_tags')
body=body.replace('        } else restore(incumbent);', '            return true;\n        }\n        restore(incumbent);\n        return false;')
assert 'return true' in body
helper='''    // Keep the uncommon extra plan's snapshots and editing work out of process's
    // main frame; its eligibility was checked using the existing edited cache.
    template<class Candidate>
    [[gnu::noinline]] bool finish_weighted_plan(const State& initial, const Candidate& c,
                                               int u, double value, Moves& chosen
                                               OP_TAG(, std::vector<uint8_t>& chosen_tags)) {
'''+body+'    }\n'
s=s[:a]+'''                    if (finish_weighted_plan(st0, c, u, value, chosen_path OP_TAG(, best_tags))) {
                        winning_operator = 4; winning_round = 0; winning_escape = false;
                    }
'''+s[b:]
s=s.replace('    Moves process(int u) {',helper+'    Moves process(int u) {',1)
p=r/'argon-req-ejecthelper';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text((r/'argon-req-ejectcache/README.md').read_text()+'''\n追加ejectの保存・復元・編集処理を専用の非インライン関数finish_weighted_planへまとめる。通常のprocessのスタックフレームと命令列へまれな追加処理を含めない。候補・呼び出し順・浮動小数点演算はejectcacheと同じで、性能差を通常比較でも確認する。\n''')
