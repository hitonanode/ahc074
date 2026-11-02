#!/usr/bin/env python3
"""Rebuild the self-contained stationary experiment from astra-rule-post."""
from pathlib import Path
here=Path(__file__).resolve().parent
source=(here.parent/'astra-rule-post/main.cpp').read_text()
start=source.index('void Comparator::optimize_rules(')
end=source.index('\nconstexpr u64 kDiagonal',start)
f=source[start:end]
f=f.replace('std::unordered_map<Bits, int, Hash> costs;', '''std::unordered_map<Bits, double, Hash> costs;
    bool weighted = false;
    std::array<std::array<double,256>,90> weight_lut{};''')
f=f.replace('''        int value = ns * diameter;
        for (const auto& b : reached)
            for (u64 w : b) value -= __builtin_popcountll(w);
        costs.emplace(goals, value);''','''        double value = ns * diameter;
        for (const auto& b : reached) {
            if (weighted) {
                for (int k=0;k<90;++k) value -= weight_lut[k][(b[k/8] >> (8*(k%8))) & 255];
            } else {
                for (u64 w : b) value -= __builtin_popcountll(w);
            }
        }
        value = std::max(0.0, value);
        costs.emplace(goals, value);''')
f=f.replace('return -1;\n        return distance_sum','return -1.0;\n        return distance_sum')
f=f.replace('std::vector<int> rel(np);','std::vector<double> rel(np);')
f=f.replace('auto matching = [&](const std::vector<int>& costs)', 'auto matching = [&](const std::vector<double>& costs)')
f=f.replace('long long total = 0;', 'double total = 0;')
f=f.replace('std::vector<std::pair<int, int>> es;', 'std::vector<std::pair<double, int>> es;')
f=f.replace('std::vector<int> trial = rel, best_rel;', 'std::vector<double> trial = rel, best_rel;')
anchor='''    double value = matching(rel), before = value;
    int candidates = 0, accepted = 0;'''
assert f.count(anchor)==1
stationary=r'''    // The policy is exactly Solver::set_generic for an unassisted shared paper:
    // shortest distance, then minimum one-step future cost, then first order.
    // Targets without generic holes are identity transitions and may be omitted.
    struct StationaryStats {
        int active = 0, iterations = 0;
        double maximum = 1.0/720, effective = 720, residual = 0;
    };
    auto stationary_weights = [&]() {
        std::vector<std::vector<int>> targets;
        for(int p=0;p<np;++p) if(pairs[p].holes) {
            const Goals goal=excluded_goals(p,-1);
            for(int side=0;side<2;++side) {
                std::vector<int> sat;
                for(int w=0;w<NW;++w) for(u64 z=goal[side][w];z;z&=z-1)
                    sat.push_back(w*64+__builtin_ctzll(z));
                assert(!sat.empty());
                targets.push_back(std::move(sat));
            }
        }
        StationaryStats stats;
        stats.active=int(targets.size());
        std::vector<double> pi(ns,1.0/ns);
        if(!targets.empty()) {
            const int nt=int(targets.size());
            std::vector<uint8_t> best_dist(nt*ns,255);
            std::vector<int> future(ns,0);
            for(int u=0;u<nt;++u) for(int s=0;s<ns;++s) {
                int bd=255;
                for(int t:targets[u]) if((bd=std::min(bd,distance(s,t)))==0)break;
                best_dist[u*ns+s]=bd;
                future[s]+=bd;
            }
            // Multiplying all future costs by nt preserves the exact tie order.
            std::vector<std::vector<std::pair<uint16_t,uint16_t>>> transitions(ns);
            for(int s=0;s<ns;++s) {
                std::array<uint16_t,720> count{};
                for(int u=0;u<nt;++u) {
                    const int bd=best_dist[u*ns+s];
                    int best=s;
                    if(bd) {
                        best=-1;int bf=1<<30;
                        for(int t:targets[u]) if(distance(s,t)==bd && future[t]<bf)
                            best=t,bf=future[t];
                        assert(best>=0);
                    }
                    ++count[best];
                }
                for(int t=0;t<ns;++t)if(count[t])transitions[s].emplace_back(t,count[t]);
            }
            std::vector<double> next_pi(ns);
            for(int iteration=0;iteration<256;++iteration) {
                std::fill(next_pi.begin(),next_pi.end(),0.0);
                for(int s=0;s<ns;++s)if(pi[s]) {
                    const double weight=pi[s]/nt;
                    for(auto [t,count]:transitions[s])next_pi[t]+=weight*count;
                }
                double residual=0;
                for(int s=0;s<ns;++s)residual+=std::abs(next_pi[s]-pi[s]);
                pi.swap(next_pi);
                stats.iterations=iteration+1;stats.residual=residual;
                if(residual<1e-12)break;
            }
        }
        double total=std::accumulate(pi.begin(),pi.end(),0.0),square=0;
        stats.maximum=0;
        for(double& w:pi){w/=total;stats.maximum=std::max(stats.maximum,w);square+=w*w;}
        stats.effective=1.0/square;
        for(int k=0;k<90;++k) {
            weight_lut[k][0]=0;
            for(int mask=1;mask<256;++mask) {
                const int bit=__builtin_ctz(unsigned(mask));
                weight_lut[k][mask]=weight_lut[k][mask&(mask-1)]+ns*pi[8*k+bit];
            }
        }
        weighted=true;
        costs.clear(); // Goal sets alone do not identify a cost after pi changes.
        return stats;
    };
    auto recost = [&]() {
        for(int p=0;p<np;++p)rel[p]=goal_cost(excluded_goals(p,-1));
        return matching(rel);
    };
    double value = matching(rel), before = value;
    StationaryStats initial_stats,last_stats,final_stats;
    int stationary_passes=0;
    double stationary_initial=-1,stationary_final=-1,last_before=-1,last_after=-1;
    int candidates = 0, accepted = 0;'''
f=f.replace(anchor,stationary)
anchor='''    for (int pass = 0; pass < sweeps && elapsed_sec() < deadline; pass++) {
        std::shuffle'''
assert f.count(anchor)==1
f=f.replace(anchor,'''    for (int pass = 0; pass < sweeps && elapsed_sec() < deadline; pass++) {
        last_stats=stationary_weights();
        value=recost();
        if(!stationary_passes){initial_stats=last_stats;stationary_initial=value;}
        ++stationary_passes;
        last_before=value;
        std::shuffle''')
anchor='''        if (!changed) break;
    }
    opq.assign'''
assert f.count(anchor)==1
f=f.replace(anchor,'''        last_after=value;
        std::cerr<<"stationary_pass_"<<pass<<"_before = "<<last_before
                 <<"\\nstationary_pass_"<<pass<<"_after = "<<last_after<<'\\n';
        if (!changed) break;
    }
    // Self-consistent final policy evaluation is a fixed-budget diagnostic. Do
    // not add it after the normal-mode deadline; the last fitted pi is reported.
    if(deadline>1e50 && stationary_passes) {
        final_stats=stationary_weights();
        stationary_final=recost();
    }
    // Keep the inherited before/after diagnostics on the same uniform measure.
    weighted=false;costs.clear();value=recost();
    std::cerr<<"stationary_passes = "<<stationary_passes
             <<"\\nstationary_initial_cost = "<<stationary_initial
             <<"\\nstationary_final_cost = "<<stationary_final
             <<"\\nstationary_initial_max = "<<initial_stats.maximum
             <<"\\nstationary_initial_effective = "<<initial_stats.effective
             <<"\\nstationary_last_max = "<<last_stats.maximum
             <<"\\nstationary_last_effective = "<<last_stats.effective
             <<"\\nstationary_last_residual = "<<last_stats.residual
             <<"\\nstationary_last_iterations = "<<last_stats.iterations
             <<"\\nstationary_final_max = "<<final_stats.maximum
             <<"\\nstationary_final_effective = "<<final_stats.effective
             <<"\\nstationary_final_residual = "<<final_stats.residual
             <<"\\nstationary_final_iterations = "<<final_stats.iterations<<'\\n';
    opq.assign''')
source=source[:start]+f+source[end:]
source=source.replace('// astra-rule-flex: astra-nonlinear with dynamically chosen visibility-witness windows.', '// astra-rule-stationary: final-pair ternary codebook fitted under a stationary generic policy.')
(here/'main.cpp').write_text(source)
