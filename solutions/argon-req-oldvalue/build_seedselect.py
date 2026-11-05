from pathlib import Path
import subprocess,sys
name=sys.argv[1];gap=sys.argv[2];novel=int(sys.argv[3])
p=Path('solutions')/name;p.mkdir()
subprocess.run(['python3','solutions/argon-req-oldvalue/build_late_cache.py',name,gap],check=True)
s=p.joinpath('main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
sub('    bool seed_valid = false;','    bool seed_valid = false, weighted_novel = false;')
sub('''        std::vector<RepeatedPlan> repeated_plans;''','''        std::vector<std::array<uint8_t, K>> previous_orders;
        std::vector<RepeatedPlan> repeated_plans;''')
sub('''                weighted_seed = {save(), ops OP_TAG(, op_tags), cost, true};''','''                weighted_seed = {save(), ops OP_TAG(, op_tags), cost, true};
                weighted_novel = std::find(previous_orders.begin(), previous_orders.end(), order) == previous_orders.end();''')
sub('''            record_future(cost);
            if (cost < best)''','''            previous_orders.push_back(order);
            record_future(cost);
            if (cost < best)''')
sub('''        if (!weighted_seed.ready || weighted_seed.cost > value +''','''        if (weighted_seed.stage != 1''' + (' || !weighted_novel' if novel else '') + ''') return path;
        if (!weighted_seed.ready || weighted_seed.cost > value +''')
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+f'''
追加処理は通常の候補編集が既に済んでいるがeject・中立探索が未完了の計画だけに限定する。未編集の候補を一から処理すること、および既に通常の勝者としてeject・中立探索を受けた計画の再探索を省く。{'さらに通常の計画と同じ初期積層になる場合は省く。' if novel else '初期積層が通常計画と同じ候補も対象とする。'}完成値との差の上限は{gap}。
''')
