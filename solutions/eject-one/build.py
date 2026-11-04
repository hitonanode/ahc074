from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'post-eject-once/main.cpp').read_text()
arrays=(p.parent/'solver-arrays/main.cpp').read_text()
for begin,end,oldbegin in [('    double adaptive_next_cost_array() const {','    // Puts paper x','    double adaptive_next_cost() const {'),('    void adaptive_insert_array(int x, int u, int barrier = -1, int mode = 2) {','    // ------------------------------------------------------------------------------------------','    void adaptive_insert(int x, int u, int barrier = -1, int mode = 2) {')]:
 a=arrays.index(begin);b=arrays.index(end,a)
 replacement=arrays[a:b].replace('_array(', '(')
 x=s.index(oldbegin);y=s.index(end,x)
 s=s[:x]+replacement+s[y:]
for a,b in [('kAnnealEnd = 1.305','kAnnealEnd = 1.205'),('kClimbEnd = 1.36','kClimbEnd = 1.26'),('1.445);','1.345);'),('perforation.deadline=1.49','perforation.deadline=1.39'),('kHelperGiveUp = 1.55','kHelperGiveUp = 1.45')]:
 assert a in s,a
 s=s.replace(a,b)
for declaration in ['    std::array<double,64> relation_gain{};std::array<long long,64> relation_count{};\n','    std::array<double,125> eject_gain{};std::array<long long,125> eject_count{};\n']:
 assert declaration in s;s=s.replace(declaration,'')
a=s.index('                                auto kind=[&](int x)')
b=s.index('                            }',a)
s=s[:a]+s[b:]
s=s.replace('                            double before_score=best_score;\n','')
needle='    std::cerr << "post_alternate = "'
s=s.replace(needle,'    std::cerr << "eject_pairs = " << solver.mid_pairs << "\\neject_trials = " << solver.mid_trials << "\\neject_accepts = " << solver.mid_accepts << "\\neject_inside = " << solver.mid_inside << \'\\n\';\n'+needle)
(p/'main.cpp').write_text(s)
