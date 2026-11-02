from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'joint-detail.cpp').read_text()
s=s.replace('''        const double before=current.value;''','''        const double before=current.value;''') # declaration is on a combined line
s=s.replace('''const double before=current.value;
        struct Node''','''const double before=current.value;
        double best_value=current.value;auto best_state=state;auto best_A=A;auto best_permutation=permutation;
        int uphill_accepted=0;
        struct Node''')
s=s.replace('''                beam.clear();for(auto&node:next){bool duplicate=false;for(auto&b:beam)duplicate|=b.s==node.s;if(!duplicate)beam.push_back(std::move(node));if(beam.size()==4)break;}''','''                beam.clear();
                // Three cheapest states plus the cheapest state with a nonlinear
                // gate in this atomic window group. Keep a route across the
                // comparator-only basin without accepting a partial design.
                int nonlinear_node=-1;
                for(int z=0;z<int(next.size());z++) {
                    bool nl=false;for(int w:windows)nl|=__builtin_popcount(gates[next[z].s[w]].o)>2;
                    if(nl){nonlinear_node=z;break;}
                }
                for(int z=0;z<int(next.size());z++){
                    bool duplicate=false;for(auto&b:beam)duplicate|=b.s==next[z].s;
                    if(!duplicate)beam.push_back(next[z]);if(beam.size()==3)break;
                }
                if(nonlinear_node>=0){bool duplicate=false;for(auto&b:beam)duplicate|=b.s==next[nonlinear_node].s;if(!duplicate)beam.push_back(next[nonlinear_node]);}
                for(auto&node:next){bool duplicate=false;for(auto&b:beam)duplicate|=b.s==node.s;if(!duplicate)beam.push_back(node);if(beam.size()==4)break;}''')
a='''            if(!beam.empty()&&beam[0].e.value<current.value-1e-9){
                restore(beam[0].s);current=std::move(beam[0].e);int changes=0;for(int j:windows)changes+=saved[j]!=state[j];++accepted;multi_accepted+=changes>=2;window_swaps+=swap_j>=0;
            }else {restore(saved);if(swap_j>=0)exchange_coordinate(swap_j,swap_h);}'''
b='''            int pick=-1;double candidate=1e100;
            for(int z=0;z<int(beam.size());z++) {
                if(beam[z].s==saved&&swap_j<0)continue;
                if(beam[z].e.value<candidate){candidate=beam[z].e.value;pick=z;}
            }
            const double temp=.05*std::pow(.025,double(t)/std::max(1,iterations-1));
            if(pick>=0 && (candidate<=current.value || rng.real()<std::exp((current.value-candidate)/temp))) {
                uphill_accepted+=candidate>current.value+1e-9;
                restore(beam[pick].s);current=std::move(beam[pick].e);
                int changes=0;for(int j:windows)changes+=saved[j]!=state[j];++accepted;multi_accepted+=changes>=2;window_swaps+=swap_j>=0;
                if(current.value<best_value){best_value=current.value;best_state=state;best_A=A;best_permutation=permutation;}
            } else {restore(saved);if(swap_j>=0)exchange_coordinate(swap_j,swap_h);}'''
assert a in s;s=s.replace(a,b)
s=s.replace('''        // Final exact graph includes extra visibility''','''        A=best_A;permutation=best_permutation;restore(best_state);
        for(auto&e:pairs){e.d=A[e.u]^A[e.v];e.fixed=.65*__builtin_popcountll(e.d>>c.G)+.04*__builtin_popcountll(e.d);}
        current=evaluate(gm);
        std::cerr<<"decoder_uphill_accepted = "<<uphill_accepted<<'\\n';
        // Final exact graph includes extra visibility''')
(p/'joint-sa.cpp').write_text(s)
