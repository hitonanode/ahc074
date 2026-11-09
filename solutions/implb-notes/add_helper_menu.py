from pathlib import Path
p=Path('solutions/d30b-req-stack/main.cpp');s=p.read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a[:80],s.count(a))
 s=s.replace(a,b)
replace('void refill_or_return(int u, FillerList olds, u64& pre_cov, FillerList& placed) {','void refill_or_return(int u, FillerList olds, u64& pre_cov, FillerList& placed, int helper_a=-1, int helper_b=-1) {')
replace('''            int x = olds[i].paper, cf = col_of[x];
            bool use = false;''','''            int x = olds[i].paper, cf = col_of[x];
            // Selected helpers must be back in their columns before run_interleave digs them.
            if(x==helper_a || x==helper_b){return_paper(x,u,1);continue;}
            bool use = false;''')
replace('    void run_interleave(int u, const Interleave::Pick& pk) {','    void run_interleave(int u, const Interleave::Pick& pk, u64 pre_cov=0) {')
replace('finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.paper].opaque);','finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.paper].opaque & ~pre_cov);')
replace('    void run_interleave_pair(int u, const PairHelperPick& pk) {','    void run_interleave_pair(int u, const PairHelperPick& pk, u64 pre_cov=0) {')
replace('finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.upper].opaque & ~paper[pk.lower].opaque);','finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.upper].opaque & ~paper[pk.lower].opaque & ~pre_cov);')
replace('    long long interleave_trials = 0, interleave_selected = 0;', '''    long long interleave_trials = 0, interleave_selected = 0;
    long long helper_menu_trials=0,helper_menu_valid=0,helper_menu_reuse=0,helper_menu_nogen=0,helper_menu_improved=0;
    double helper_menu_cost_gain=0;
    static bool helper_menu_enabled() {
#ifdef LOCAL_BENCH
        if(const char* p=std::getenv("D30B_HELPER_MENU"))return std::atoi(p)!=0;
#endif
        return true;
    }''')
replace('    // The helper plans of request u from st0 (cost as in process); updates best / best_ops / best_state.', '''    // A second return menu for one selected helper set. pre_cov uses physical
    // internal window bits: helpers COVER their opaque holes, not their own holes.
    bool prepare_helper_menu(int u,const State& st0,int x,int y,u64& pre_cov) {
        start_plan(st0);
        const int d=ded[u];
        pre_cov=hmask & ~paper[d].opaque & (paper[x].opaque | (y<0?0:paper[y].opaque));
        int previous=top_d,lvl=-1;
        u64 cov=0;
        if(previous>=0 && previous!=x && previous!=y && previous!=d)
            lvl=level_for(previous,d,hmask & ~paper[d].opaque & ~pre_cov,u,cov);
        if(lvl>=0) {
            FillerList vis_old,def_old;
            for(const auto& f:fillers)(visible(f.paper)?vis_old:def_old).push_back(f);
            FillerList placed={{previous,lvl,col_of[previous]}};
            pre_cov|=cov;
            refill_or_return(u,vis_old,pre_cov,placed,x,y);
            if(invalid)return false;
            {OP_LABEL(kOpReuse);move_to_level(previous,lvl);}
            top_d=-1;
            refill_or_return(u,def_old,pre_cov,placed,x,y);
            for(const auto& f:placed)fillers.push_back(f);
            ++helper_menu_reuse;
        } else {
            if(top_d>=0)return_paper(top_d,u,1);
            FillerList olds=fillers,placed;
            refill_or_return(u,olds,pre_cov,placed,x,y);
            for(const auto& f:placed)fillers.push_back(f);
        }
        if(invalid)return false;
        if(order[0]!=kCapPaper){++helper_menu_nogen;return false;}
        for(int i=0;i<M;++i)if(order[i+1]>=M){++helper_menu_nogen;return false;}
        if(!in_column(x,col_of[x]) || (y>=0 && !in_column(y,col_of[y])))return false;
        return true;
    }
    // The helper plans of request u from st0 (cost as in process); updates best / best_ops / best_state.''')
old='''        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            keep(plan_cost(ops.size()));
        };
        for (const auto& item : pair_picks) {'''
new='''        bool menu_trial=false;
        double clean_best=1e100,menu_best=1e100;
        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            const double cost=plan_cost(ops.size());
            if(menu_trial){++helper_menu_valid;menu_best=std::min(menu_best,cost);}
            else clean_best=std::min(clean_best,cost);
            keep(cost);
        };
        for (const auto& item : pair_picks) {'''
replace(old,new)
old='''            run_interleave(u, item.second);
            finish();
        }
    }

    // ==== Post-processing: deletions and new anchors of the edits ===='''
new='''            run_interleave(u, item.second);
            finish();
        }
        if(helper_menu_enabled() && (st0.top_d>=0 || !st0.fillers.empty())) {
            menu_trial=true;
            if(!pair_picks.empty()) {
                ++helper_menu_trials;
                const auto& pk=pair_picks.front().second;
                u64 pre_cov=0;
                if(prepare_helper_menu(u,st0,pk.upper,pk.lower,pre_cov)) {
                    ++interleave_trials;run_interleave_pair(u,pk,pre_cov);finish();
                }
            }
            if(!picks.empty()) {
                ++helper_menu_trials;
                const auto& pk=picks.front().second;
                u64 pre_cov=0;
                if(prepare_helper_menu(u,st0,pk.paper,-1,pre_cov)) {
                    ++interleave_trials;run_interleave(u,pk,pre_cov);finish();
                }
            }
            if(clean_best<1e50 && menu_best<clean_best-1e-9) {
                ++helper_menu_improved;helper_menu_cost_gain+=clean_best-menu_best;
            }
        }
    }

    // ==== Post-processing: deletions and new anchors of the edits ===='''
replace(old,new)
replace('              << "\\ninterleave_trials = " << solver.interleave_trials', '''              << "\\nhelper_menu_trials = " << solver.helper_menu_trials
              << "\\nhelper_menu_valid = " << solver.helper_menu_valid
              << "\\nhelper_menu_reuse = " << solver.helper_menu_reuse
              << "\\nhelper_menu_nogen = " << solver.helper_menu_nogen
              << "\\nhelper_menu_improved = " << solver.helper_menu_improved
              << "\\nhelper_menu_cost_gain = " << solver.helper_menu_cost_gain
              << "\\ninterleave_trials = " << solver.interleave_trials''')
p.write_text(s)
