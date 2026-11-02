#!/usr/bin/env python3
"""採用する計画を変えず、追加した候補が列間の相対順序を変えるか分類する。"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'fast.cpp').read_text()
metrics='''    long long generated_cross=0, retained_cross=0, retained_total=0;
    long long selected_cross=0, selected_generic_cross=0, selected_generic_only=0;
    double advantage_cross=0, advantage_own=0;
    // Whether any pair of dedicated papers of different columns reverses its relative order.
    // Papers inside the same column may change order without being counted as cross-column.
    bool crosses_columns(const State& a,const State& b) const {
        std::array<int,K> pos{};
        for(int i=0;i<K;i++)pos[a.order[i]]=i;
        for(int i=0;i<K;i++) {
            const int x=b.order[i];
            if(col_of[x]<0)continue;
            for(int j=i+1;j<K;j++) {
                const int y=b.order[j];
                if(col_of[y]>=0 && col_of[x]!=col_of[y] && pos[x]>pos[y])return true;
            }
        }
        return false;
    }
    bool crosses_generic(const State& a,const State& b) const {
        std::array<int,K> pa{},pb{};
        for(int i=0;i<K;i++)pa[a.order[i]]=i,pb[b.order[i]]=i;
        for(int x=0;x<K;x++)if(col_of[x]>=0)
            for(int g=0;g<M;g++)if((pa[x]<pa[g])!=(pb[x]<pb[g]))return true;
        return false;
    }
'''
needle='    int expansion_mode = 0;'
assert needle in s
s=s.replace(needle,metrics+needle)
s=s.replace('        oracle_candidates += endplans.size();','''        for(int i=original_candidates;i<int(endplans.size());i++)
            generated_cross+=crosses_columns(base_state,endplans[i].state);
        oracle_candidates += endplans.size();''')
needle='        int best = 0;\n        double bv = 1e100;'
assert needle in s
s=s.replace(needle,'''        for(int i=original_candidates;i<int(endplans.size());i++) {
            retained_total++;
            retained_cross+=crosses_columns(base_state,endplans[i].state);
        }
'''+needle)
needle='        expanded_selected+=best>=original_candidates;'
assert needle in s
s=s.replace(needle,'''        if(best>=original_candidates) {
            const bool cross=crosses_columns(base_state,endplans[best].state);
            selected_cross+=cross;
            const bool generic=crosses_generic(base_state,endplans[best].state);
            selected_generic_cross+=generic;
            selected_generic_only+=generic && !cross;
            if(cross)advantage_cross+=endplans[0].value-endplans[best].value;
            else advantage_own+=endplans[0].value-endplans[best].value;
        }
'''+needle)
needle='<< ",\\\"prefix_disagree\\\":["'
assert needle in s
s=s.replace(needle,'''<< ",\\\"generated_cross\\\":" << sim.generated_cross
                      << ",\\\"retained_cross\\\":" << sim.retained_cross
                      << ",\\\"retained_total\\\":" << sim.retained_total
                      << ",\\\"selected_cross\\\":" << sim.selected_cross
                      << ",\\\"selected_generic_cross\\\":" << sim.selected_generic_cross
                      << ",\\\"selected_generic_only\\\":" << sim.selected_generic_only
                      << ",\\\"advantage_cross\\\":" << sim.advantage_cross
                      << ",\\\"advantage_own\\\":" << sim.advantage_own
                      '''+needle)
(ROOT/'choice_audit.cpp').write_text(s)
