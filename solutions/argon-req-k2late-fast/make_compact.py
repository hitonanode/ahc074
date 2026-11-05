from pathlib import Path
import sys
name,donor=sys.argv[1:]
p=Path('solutions')/name
assert not p.exists();p.mkdir()
s=(Path('solutions')/donor/'main.cpp').read_text()
s=s.replace('int joint_rank = 0;', 'bool second_solution = false;').replace('joint_rank','second_solution')
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b,1)
sub('    inline static std::vector<std::vector<Cand>> joint_choices;', '''    inline static std::vector<Cand> joint_second;
    inline static bool joint_second_ready = false;''')
sub('''        joint_choices = {primary};
        for (int i=0; i<count[H] && joint_choices.size()<2; ++i) {''','''        joint_second.clear();
        joint_second_ready = false;
        for (int i = 0; i < count[H] && !joint_second_ready; ++i) {''')
sub('''            std::vector<Cand> picks;
            for (int node=q.node; node>=0; node=nodes[node].previous) picks.push_back(nodes[node].interval);
            joint_choices.push_back(std::move(picks));''','''            for (int node = q.node; node >= 0; node = nodes[node].previous)
                joint_second.push_back(nodes[node].interval);
            joint_second_ready = true;''')
sub('''            if (opt.second_solution >= int(joint_choices.size())) { invalid = true; return; }
            picks = joint_choices[opt.second_solution];''','''            if (!joint_second_ready) { invalid = true; return; }
            picks = joint_second;''')
sub('''        joint_choices.clear();''','''        joint_second_ready = false;''')
sub('opts.push_back({1, 5, true, true, false, 1});', 'opts.push_back({1, 5, true, true, false, true});')
# Align the inner candidate-generation block and the small fixed-state recurrence.
a=s.index('        joint_second_ready = false;',s.index('    void run_joint('))
b=s.index('\n        }\n\n        if (opt.value_fillers',a)
s=s[:a]+''.join('    '+line if line.strip() else line for line in s[a:b].splitlines(keepends=True))+s[b:]
s=s.replace('for (int j=0; j<count[cd.lvl]; ++j)', 'for (int j = 0; j < count[cd.lvl]; ++j)')
(p/'main.cpp').write_text(s)
(p/'README.md').write_text((Path('solutions')/donor/'README.md').read_text()+'''
第2解だけを専用scratchへ保持し、既存の第1解の余分なコピーを省く。実験専用の順位整数は二値の印に整理した。候補の列挙・同点の扱い・後処理順は変えない。
''')
print(p)
