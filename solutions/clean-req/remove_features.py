from pathlib import Path
import argparse,re
p=argparse.ArgumentParser()
for flag in ['memory','stay','canon','shared-vis','cross-memo']:p.add_argument('--'+flag,action='store_true')
a=p.parse_args();s=Path('solutions/clean-req-refactor/main.cpp').read_text()
def replace(old,new,n=1):
 global s
 assert s.count(old)==n,(old[:100],s.count(old),n);s=s.replace(old,new)
def remove_block(start,extend_newline=True):
 global s
 pos=s.index(start);b=s.index('{',pos);depth=1;i=b+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 if extend_newline and s[i:i+1]=='\n':i+=1
 s=s[:pos]+s[i:]
if a.memory:
 remove_block('        if (query_memory_mode() >= 3 && !query_memory.empty()) {')
 start=s.index('    // Keep one final plan per target.')
 end=s.index('    // Re-edit only after an accepted ejection.',start)
 s=s[:start]+'''    // Query-memory plans were removed after ablation; retain their metric names.
    long long qm_requests = 0;
    void report_query_memory() const {
        for (const char* name : {"qm_template_duplicate", "qm_template_saved", "qm_template_trials",
                                 "qm_template_legal", "qm_mode"}) std::cerr << name << " = 0\\n";
        std::cerr << "qm_requests = " << qm_requests << '\\n';
        for (const char* name : {"qm_seen", "qm_exact_state", "qm_local_state", "qm_trials", "qm_legal",
                                 "qm_candidates", "qm_selected", "qm_skipped"})
            std::cerr << name << " = 0\\n";
    }

'''+s[end:]
 replace('        const int qm_mode = query_memory_mode();\n','')
 replace('        if (qm_mode && query_memory.empty()) query_memory.resize(P);\n','')
 remove_block('        if (qm_mode && query_memory[u].ready) {')
 remove_block('        if ((qm_mode == 1 || qm_mode == 2) && query_memory[u].ready) {')
 replace('        if (qm_mode) remember_query(u, st0, chosen_path OP_TAG(, best_tags));\n','')
 assert 'query_memory_mode' not in s
if a.stay:
 replace('return the previous product (1/2), reuse it as a filler (3), or keep it (4);',
         'return the previous product (1/2), or reuse it as a filler (3);')
 replace('        int stay = -1;\n','')
 replace('''    // An old filler above the bottom of the generic layer (the previous lifted paper left under the new one by the stay
    // plan) may show its colors on the generic holes of the next paper D; where they differ from A_u
''','''    // A filler above the bottom of the generic layer may show on the generic holes of D;
    // where its colors differ from A_u
''')
 remove_block('        if (opt.ret_mode == 4) {')
 remove_block('        if (stay >= 0) {')
 replace('        if (prev_ok)\n            for (int fm : fms) opts.push_back({4, fm, true});\n','')
if a.canon:
 replace('        bool fast_canon = get("CANON", 0);\n','')
 replace('        std::array<int, K> mono_start;\n        std::array<u64, K> mono_mask;\n','')
 start=s.index('            const int col = col_of[k];',s.index('    void prepare_post_context'))
 end=s.index('\n        }',start);s=s[:start]+s[end:]
 start=s.index('    // Exact canonicalization using unchanged, monotonically ordered column runs.')
 end=s.index('    // Under LOCAL_BENCH, tags holds',start);s=s[:start]+s[end:]
 replace('                if (cfg.fast_canon) canonicalize_post(prev, moved, breaks);\n                else canonicalize();','                canonicalize();')
if a.shared_vis:
 replace('        bool shared_vis = get("SHARED_VIS", 0);\n','')
 replace('        std::array<int, K> first_visible, last_visible;\n','')
 replace('                bool visibility_ready = false;\n','')
 start=s.index('                    if (cfg.shared_vis) {');mid=s.index('                    } else {\n                        replay_order = initial_bytes;',start)
 end=s.index('                    }\n                    if (latest < 0)',mid)
 body=s[mid+len('                    } else {\n'):end]
 body=''.join(line[4:] if line.startswith('    ') else line for line in body.splitlines(True))
 s=s[:start]+body+s[end+len('                    }\n'):]
if a.cross_memo:
 replace('        bool cross_memo = get("CROSS_MEMO", 0);\n','')
 replace('        std::vector<uint8_t> prior_fillers;  // only the old paper sequence affects canonical priority\n','')
 replace('        const u64 generation = cfg.cross_memo ? memo_generation : ++memo_generation;','        const u64 generation = ++memo_generation;')
 remove_block('                    if (memo_hit && cfg.cross_memo) {')
 remove_block('                        if (cfg.cross_memo) {')
 replace('''        // Weights/targets stay fixed during a request. Final-order values can cross pass boundaries
        // if canonicalization's old filler priority is also identical; a new request invalidates them.
        if (search_config().cross_memo) ++memo_generation;
''','')
Path('solutions/clean-req/main.cpp').write_text(s)
print('lines',len(s.splitlines()))
