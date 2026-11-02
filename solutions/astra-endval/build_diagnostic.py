#!/usr/bin/env python3
"""研究コードへ候補拡張と診断を足す。実行中のresearchは上書きしない。"""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'research.cpp').read_text()
s=s.replace('double value = 0;\n    };','double value = 0;\n        double next_moves = 0, next_terminal = 0;\n        std::array<double,6> prefix{};\n    };')
s=s.replace('double rollout_value(const EndPlan& p,', 'double rollout_value(EndPlan& p,')
s=s.replace('double sum = 0;\n        for (int v : targets)', 'double sum = 0, sm = 0, st = 0; int ni = 0;\n        constexpr std::array<int,6> ns{1,4,16,64,128,255};\n        for (int v : targets)')
s=s.replace('sum += path.size() + terminal_weight * (adaptive_next_cost() + kFillerCharge * fillers.size());', '''sm += path.size();
            st += adaptive_next_cost() + kFillerCharge * fillers.size();
            sum = sm + terminal_weight * st;
            ni++;
            for(int i=0;i<6;i++) if(ni==ns[i]) p.prefix[i] = p.path.size()+sum/ni;''')
s=s.replace('return p.path.size() + sum / targets.size();', 'p.next_moves=sm/targets.size(); p.next_terminal=st/targets.size();\n        return p.path.size() + sum / targets.size();')
s=s.replace('endplans.clear();\n        collecting', 'const State initial=save();\n        endplans.clear();\n        collecting')
s=s.replace('oracle_candidates += endplans.size();', '''const int original_candidates=endplans.size();
        if(expansion_mode) {
            EndPlan baseplan{base_state,base,0};
            expand_plans(initial,baseplan,u);
        }
        oracle_candidates += endplans.size();''')
# Optional screening only for additional states: retain all original planner choices.
s=s.replace('int best = 0;\n        double bv', '''const int extra_keep=env_int("EXPAND_KEEP")>0?env_int("EXPAND_KEEP"):4;
        if(expansion_mode && int(endplans.size())>original_candidates+extra_keep) {
            const int screen_count=env_int("EXPAND_SCREEN")>0?env_int("EXPAND_SCREEN"):16;
            std::vector<int> screen_targets(targets.begin(),targets.begin()+std::min<int>(screen_count,targets.size()));
            for(int i=original_candidates;i<int(endplans.size());i++) endplans[i].value=rollout_value(endplans[i],screen_targets);
            std::stable_sort(endplans.begin()+original_candidates,endplans.end(),[](const auto& a,const auto& b){return a.value<b.value;});
            endplans.resize(original_candidates+extra_keep);
        }
        int best = 0;
        double bv''')
s=s.replace('oracle_changed += endplans[best].state.order != base_state.order;', '''if(endplans.size()>1) {
            advantage += endplans[0].value-endplans[best].value;
            current_delta += double(endplans[best].path.size())-base.size();
            next_delta += endplans[best].next_moves-endplans[0].next_moves;
            terminal_delta += endplans[best].next_terminal-endplans[0].next_terminal;
            for(int j=0;j<6;j++) {
                constexpr std::array<int,6> ns{1,4,16,64,128,255};
                if(ns[j]>oracle_samples)continue;
                int b=0;
                for(int i=1;i<int(endplans.size());i++) if(endplans[i].prefix[j]<endplans[b].prefix[j]-1e-9)b=i;
                prefix_disagree[j] += b!=best;
                prefix_regret[j] += endplans[b].value-endplans[best].value;
            }
        }
        expanded_selected+=best>=original_candidates;
        oracle_changed += endplans[best].state.order != base_state.order;''')
s=s.replace('int oracle_samples = 0, oracle_step = 0;', '''double advantage=0,current_delta=0,next_delta=0,terminal_delta=0;
    std::array<long long,6> prefix_disagree{};
    std::array<double,6> prefix_regret{};
    int oracle_samples = 0, oracle_step = 0;''')
s=s.replace('    // Mutually exclusive move accounting', (root/'expand.inc').read_text()+'\n    // Mutually exclusive move accounting')
s=s.replace('sim.oracle_samples = env_int("ORACLE_SAMPLES");', 'sim.oracle_samples = env_int("ORACLE_SAMPLES");\n            sim.expansion_mode=env_int("EXPAND");')
s=s.replace('<< ",\\\"req_sec\\\":" << elapsed_sec()-started', '''<< ",\\\"advantage\\\":" << sim.advantage
                      << ",\\\"current_delta\\\":" << sim.current_delta << ",\\\"next_delta\\\":" << sim.next_delta
                      << ",\\\"terminal_delta\\\":" << sim.terminal_delta
                      << ",\\\"expanded_total\\\":" << sim.expanded_total << ",\\\"expanded_selected\\\":" << sim.expanded_selected
                      << ",\\\"prefix_disagree\\\":[" << sim.prefix_disagree[0] << ',' << sim.prefix_disagree[1] << ',' << sim.prefix_disagree[2] << ',' << sim.prefix_disagree[3] << ',' << sim.prefix_disagree[4] << ',' << sim.prefix_disagree[5] << ']'
                      << ",\\\"prefix_regret\\\":[" << sim.prefix_regret[0] << ',' << sim.prefix_regret[1] << ',' << sim.prefix_regret[2] << ',' << sim.prefix_regret[3] << ',' << sim.prefix_regret[4] << ',' << sim.prefix_regret[5] << ']'
                      << ",\\\"req_sec\\\":" << elapsed_sec()-started''')
# This research executable can also be exercised by the real tester, without any simulator tail.
s=s.replace('kFastAfter = 1.80', 'kFastAfter = 1e9')
s=s.replace('    // as6-cap38p0: the cap is output', '''    solver.oracle_samples=env_int("ORACLE_SAMPLES");
    solver.expansion_mode=env_int("EXPAND");
    // as6-cap38p0: the cap is output''')
(root/'diagnostic.cpp').write_text(s)
