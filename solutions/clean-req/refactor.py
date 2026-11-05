from pathlib import Path
import re
s=Path('solutions/time-alloc/main.cpp').read_text()
def replace(old,new,n=1):
 global s
 assert s.count(old)==n,(old[:100],s.count(old),n)
 s=s.replace(old,new)
def between(start,end,new):
 global s
 a=s.index(start);b=s.index(end,a);s=s[:a]+new+s[b:]
# The same anchor conversion serves post-processing and optional query replay.
a=s.index('        auto anchorize = [&](');b=s.index('        auto edits = anchorize',a)
old=s[a:b]
body=old[old.index('            ByteOrder ord = initial_bytes;'):old.rindex('        };')]
body=body.replace('            ByteOrder ord = initial_bytes;','            ByteOrder ord = initial;')
body='\n'.join(line[4:] if line.startswith('    ') else line for line in body.splitlines())+'\n'
helper='''    // Convert depths to predecessor IDs; later replay may start from a different stack.
    static std::vector<Edit> anchorize(const ByteOrder& initial,
                                      const std::vector<std::pair<int, int>>& path
                                      OP_TAG(, const std::vector<uint8_t>& labels)) {
'''+body+'    }\n'
s=s[:a]+s[b:]
replace('    // An order of the papers as a doubly linked list:',helper+'    // An order of the papers as a doubly linked list:')
s=re.sub(r'(?<!::)anchorize\((input_ops|best_ops)',r'anchorize(initial_bytes, \1',s)
a=s.index('        ByteOrder ord = initial.order;',s.index('    void remember_query'))
b=s.index('\n    }',a)
s=s[:a]+'        remembered.edits = anchorize(initial.order, path OP_TAG(, tags));'+s[b:]
# A common stack relocation and plan reset, without touching visibility checks or labels.
old='''        const int k = order[i];
        if (i < d)
            std::copy(order.begin() + i + 1, order.begin() + d + 1, order.begin() + i);
        else
            std::copy_backward(order.begin() + d, order.begin() + i, order.begin() + i + 1);
        order[d] = k;'''
replace(old,'        shift_byte(order, i, d);')
replace('''        if (ix + 1 == i) return;
        if (check_vis && !visible_at(k, i)) invalid = true;
        const int dest = ix - int(ix > i) + 1;  // just below x once k is taken out
        shift_paper(i, dest);
        ops.push_back({k, dest});
        OP_TAG(op_tags.push_back(op_tag);)''','''        move_from(k, i, ix - int(ix > i) + 1);''')
reset='''    void start_plan(const State& initial) {
        restore(initial);
        ops.clear();
        OP_TAG(op_tags.clear();)
        invalid = false;
    }
'''
pos=s.index('    // ==== Request plans: helpers inside the generic layer ====')
s=s[:pos]+reset+'\n'+s[pos:]
# Existing reset blocks (the implementation itself is outside the pattern's argument set).
s=re.sub(r'(?m)^( +)restore\((st0|initial)\);\n\1ops.clear\(\);\n\1OP_TAG\(op_tags.clear\(\);\)\n\1invalid = false;',lambda m:m.group(0) if s[max(0,m.start()-60):m.start()].endswith('void start_plan(const State& initial) {\n') else m[1]+'start_plan('+m[2]+');',s)
# Two equivalent linked-list splices, preserving caller checks.
helper='''    // Move k immediately after a; kRoot is the sentinel for the top and bottom.
    static void splice_after(Links& next, Links& prev, int k, int a) {
        if (prev[k] == a) return;
        next[prev[k]] = next[k];
        prev[next[k]] = prev[k];
        const int b = next[a];
        next[a] = k;
        prev[k] = a;
        next[k] = b;
        prev[b] = k;
    }
'''
replace('    struct PostContext {',helper+'    struct PostContext {')
for nx,pv in [('next','prev'),('nx','pv')]:
 pattern=r'(?m)^( +)if \('+pv+r'\[k\] == a\) continue;\n\1'+nx+r'\['+pv+r'\[k\]\] = '+nx+r'\[k\];\n\1'+pv+r'\['+nx+r'\[k\]\] = '+pv+r'\[k\];\n\1int b = '+nx+r'\[a\];\n\1'+nx+r'\[a\] = k;\n\1'+pv+r'\[k\] = a;\n\1'+nx+r'\[k\] = b;\n\1'+pv+r'\[b\] = k;'
 s,n=re.subn(pattern,lambda m:m[1]+f'splice_after({nx}, {pv}, k, a);',s);assert n==1,(nx,n)
# Eject/re-edit sequence shared by the ordinary, alternative and expanded plans.
helper='''    // Re-edit only after an accepted ejection. Keep ordinary stage/round profiler labels.
    std::vector<std::pair<int, int>> polish_ejects(const State& initial,
            std::vector<std::pair<int, int>> path, int u OP_TAG(, std::vector<uint8_t>& tags),
            int rounds, [[maybe_unused]] bool ordinary = false) {
        for (int round = 0; round < rounds; ++round) {
            F3_DIAG(if (ordinary) { f3_stage = 2; f3_round = round; })
            const auto before = eject_accepts;
            if (round) path = post_optimize(initial, std::move(path), u OP_TAG(, tags), false);
            path = post_optimize(initial, std::move(path), u OP_TAG(, tags), true);
            if (eject_accepts == before) break;
        }
        return path;
    }

'''
replace('    // ==== Request processing (process) ====',helper+'    // ==== Request processing (process) ====')
old='''        for (int round = 0; round < 4; round++) {
            F3_DIAG(f3_stage = 2; f3_round = round;)
            const auto before_eject = eject_accepts;
            if (round) chosen_path = post_optimize(st0, std::move(chosen_path), u OP_TAG(, best_tags), false);
            chosen_path = post_optimize(st0, std::move(chosen_path), u OP_TAG(, best_tags), true);
            if (eject_accepts == before_eject) break;
        }'''
replace(old,'        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);')
for rounds in ['4','cfg.plan_ejects']:
 old='''                    for (int it = 0; it < ROUNDS; it++) {
                        const auto before = eject_accepts;
                        if (it) path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false);
                        path = post_optimize(st0, std::move(path), u OP_TAG(, tags), true);
                        if (eject_accepts == before) break;
                    }'''.replace('ROUNDS',rounds)
 replace(old,'                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), '+rounds+');')
# Shared helper placement; the callers retain their distinct lift/invalid ordering.
a=s.index('    void run_interleave(')
helper='''    void set_helper_goal(int goal) {
        OP_LABEL(kOpGen);
        for (auto [k, depth] : comparator.path(interleave->state(order), goal)) move(k, depth + 1);
    }
    bool insert_helper(int k, int depth) {
        const int c = col_of[k];
        for (int it = 0; column_top(c) != k; ++it) {
            if (it >= K || invalid) { invalid = true; return false; }
            OP_LABEL(kOpHdig);
            dig(c, k);
        }
        OP_LABEL(kOpHelp);
        move(k, depth);
        fillers.push_back({k, 0, c});
        return true;
    }
'''
s=s[:a]+helper+s[a:]
old='''        const int s = interleave->state(order);
        {
            OP_LABEL(kOpGen);
            for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth + 1);
        }'''
replace(old,'        set_helper_goal(pk.goal);',2)
a=s.index('        auto get_helper =');b=s.index('        if (invalid) return;',a)
s=s[:a]+'''        if (c < l) insert_helper(pk.paper, 1 + pk.depth);  // shallower columns must be dug before D
        lift(d);
        if (c > l) insert_helper(pk.paper, 2 + pk.depth);
'''+s[b:]
a=s.index('            for (int it = 0; column_top(c) != x; it++) {',s.index('    void run_interleave_pair'))
b=s.index('            placed++;',a)
s=s[:a]+'''            if (!insert_helper(x, 1 + depth + placed + (lifted ? 1 : 0))) return;
'''+s[b:]
# Concise section explanations, retaining legality and enumeration invariants.
between('    // The moves for request u:', '    long long unsafe_plans', '''    // Simulate plan options, a filler-chain plan and helper plans from the same starting stack.
    // Keep valid candidates (correct display, <=2K moves, reachable fillers), edit the best
    // kPostCandidates, then polish by ejection and neutral rewrites (F3_NEUTRAL=0 disables neutral).
    // If none is valid, try the plain plan; return no moves if even that plan is illegal.
''')
between('    // Post-processing of the chosen plan:', '    long long eject_pairs', '''    // Edits are "paper goes below anchor" (anchor -1: top), replayed with recomputed depths.
    // Accept only legal moves, display A_u, reachable fillers, and a lower plan_cost.
    // Edit passes try deletions, new anchors for old extras/repeated papers, and both together.
    // Eject passes replace two edits by one repair; neutral collection also tries two repairs.
''')
between('    // Helper plans (Interleave), tried after the plan options', '    std::shared_ptr<Interleave>', '''    // Return the previous product and fillers, order the generic layer, and insert one or two
    // helpers at its gaps. Dig shallower columns before lifting D, deeper columns afterwards;
    // cover remaining handle holes with the usual interval-DP fillers and digs.
''')
replace('''            // This snapshot is made before any extra operator or extra plan: exactly the ordinary

''','''            // Baseline for the heavy traces: before extra operators or plans.
''')
replace('''        // The old greedy algorithm always removes the topmost visible pending paper.
        // A lower removal cannot expose a paper above it. Thus this top-down pass performs
        // exactly those removals; a pending paper still hidden here can never be removed.''','''        // A lower removal cannot expose a paper above it. In this top-down pass,
        // a pending paper still hidden when reached can never be removed.''')
# Only whitespace repair at visibly under-indented profile scopes.
s=re.sub(r'(?m)^        CF_SCOPE\((evaluate|neutral_edits)\);',r'            CF_SCOPE(\1);',s)
# Declare each experiment field next to its switch and default; no duplicate field list.
a=s.index('    struct SearchConfig {');b=s.index('    F3_DIAG(int f3_stage',a)
old=s[a:b]
fields=old[:old.index('    static const SearchConfig& search_config()')]
types={}
for typ,decl in re.findall(r'        (int|bool|double) ([^;]+);',fields):
    for name in decl.split(','):types[name.strip()]=typ
assign=re.findall(r'            out\.(\w+) = ([^;]+);',old)
assert len(assign)==len(types),(len(assign),len(types))
new="""    struct SearchConfig {
        static int get(const char* name, int fallback) {
            const char* value = search_env(name);
            return value ? std::atoi(value) : fallback;
        }
        static double number(const char* name, double fallback) {
            const char* value = search_env(name);
            return value ? std::atof(value) : fallback;
        }
        // MODE=0 is the replay-comparison preset; explicit F3_* settings override presets.
        const int mode = std::clamp(get("MODE", 1), 0, 2);
"""
for name,expr in assign:new+='        '+types[name]+' '+name+' = '+expr+';\n'
new+="""    };
    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return config;
    }
"""
s=s[:a]+new+s[b:]
# One initial order representation is enough; paper IDs are bytes in both consumers.
replace('std::array<int, K> position, order;', 'std::array<int, K> position;')
replace('c.order[j] = c.bytes[j] = k;', 'c.bytes[j] = k;')
s=s.replace('post_context.order', 'post_context.bytes')
# Give the common move-list type a name inside Solver, without changing its interface type.
a=s.index('struct Solver {');b=s.index('// ==== Emergency design ====',a)
part=s[a:b].replace('std::vector<std::pair<int, int>>', 'Moves')
part=part.replace('struct Solver {', 'struct Solver {\n    using Moves = std::vector<std::pair<int, int>>;')
s=s[:a]+part+s[b:]
# Fix indentation of nested profiler/replay blocks; no statement changes.
a=s.index('            CF_SCOPE(eval_replay);');b=s.index('            }\n            CF_SCOPE(eval_value);',a)
s=s[:a]+''.join(('    '+line if line.strip() else line) for line in s[a:b].splitlines(True))+s[b:]
s=s.replace('            CF_SCOPE(neutral_edits);','                        CF_SCOPE(neutral_edits);')
a=s.index('                    prepare_columns();',s.index('void eject_repairs'))
b=s.index('                    }\n                    if (anchors.empty())',a)
s=s[:a]+''.join(('    '+line if line.strip() else line) for line in s[a:b].splitlines(True))+s[b:]
Path('solutions/clean-req/main.cpp').write_text(s)
print('lines',len(s.splitlines()))
