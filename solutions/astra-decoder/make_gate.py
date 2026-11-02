from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'model.cpp').read_text();old=(p/'priorgate.cpp').read_text()
a=s.index('struct Comparator {');b=s.index('// Closure of a relation bit matrix',a)
x=old.index('struct Comparator {');y=old.index('// Closure of a relation bit matrix',x)
s=s[:a]+old[x:y]+s[b:]
a=s.index('}  // namespace\n\nint main()')
s=s[:a]+(p/'gate_search.inc').read_text()+'\n'+s[a:]
s=s.replace('''        comp.rebuild();
        des =''','''        comp.rebuild();
        if (int trials = env_int("GATE_TRIALS"); trials > 0) {
            AtomicGateSearch search(comp, A, env_int("GATE_COMPARATORS"));
            search.run(trials);
        }
        des =''')
s=s.replace('''        auto estimate = [&](u64 a, u64 b) {
            const auto reach''','''        auto estimate = [&](u64 a, u64 b) {
            if (comp.nonlinear) return 0.5 * (comp.mean_moves(a, a ^ b) + comp.mean_moves(b, a ^ b));
            const auto reach''')
(p/'gates.cpp').write_text(s)
