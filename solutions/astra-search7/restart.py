"""現在値が最良値から離れたとき、最良割り当てを復元して探索を続ける。"""
def restart(t,gap,interval):
    needle='    long long forced_steps = 0, tabu_skips = 0;'
    helper='''    long long best_returns=0;
    int last_return_it=0;
    auto return_best = [&] {
        ++epoch; ++best_returns;
        mask=best_mask; pol=best_pol; order=best_order;
        std::fill(which.begin(),which.end(),-1);
        hm=kActiveWindows;
        for (int e=0;e<ne;++e) {
            counts[e]=__builtin_popcountll(mask[e]); hm &= ~mask[e];
            for (u64 q=mask[e];q;q&=q-1) which[__builtin_ctzll(q)]=e;
        }
        nvalid=0;
        for (int p=0;p<np;++p) {
            pair_state(pairs.au[p],pairs.diff[p],pairs.dir[p],pairs.rel[p]);
            if (pairs.rel[p]) valid[nvalid++]=p;
        }
        cur=matching_cost(pairs.rel.data(),hm);
        selected=candidate_selected; screen_dirty=true;
        escape_floor=1e30; escape_valid=false;
        std::fill(tabu_epoch.begin(),tabu_epoch.end(),0);
    };
'''
    t=t.replace(needle,helper+needle,1)
    needle='        stats.iterations++;'
    addition='''
        if ((it&15)==0 && it-last_return_it>=INTERVAL && cur>best+GAP) {
            return_best(); last_accept_it=last_return_it=it;
        }'''.replace('INTERVAL',str(interval)).replace('GAP',str(gap))
    t=t.replace(needle,needle+addition,1)
    t=t.replace('    last_accept_it = 0;','    last_accept_it = 0; last_return_it=0;',1)
    needle='            stats.climb_steps = it + 1;'
    t=t.replace(needle,needle+addition,1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "best_returns = " << best_returns << '\n';
    stats.gobj_after = cur;''',1)
    return t
