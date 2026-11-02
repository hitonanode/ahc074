from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'gates12.cpp').read_text()
s=s.replace('Comparator&c;const std::vector<u64>&A;std::vector<Gate>gates;', 'Comparator&c;std::vector<u64>&A;std::vector<int>&permutation;std::vector<Gate>gates;')
s=s.replace('int accepted=0,multi_accepted=0;', 'int accepted=0,multi_accepted=0,window_swaps=0;')
s=s.replace('AtomicGateSearch(Comparator&comp,const std::vector<u64>&a,bool only):c(comp),A(a),comparisons_only(only)', 'AtomicGateSearch(Comparator&comp,std::vector<u64>&a,std::vector<int>&perm,bool only):c(comp),A(a),permutation(perm),comparisons_only(only)')
s=s.replace('''    void run(int iterations){''','''    // A generic/handle coordinate exchange and the decoder edits are one move.
    // Pair prices are rebuilt on both acceptance and rejection; the final design
    // sees exactly the same coordinates and candidate prices as this search.
    void exchange_coordinate(int j,int h){
        for(auto&a:A)if(((a>>j)^(a>>h))&1)a^=(1ULL<<j)|(1ULL<<h);
        std::swap(permutation[j],permutation[h]);
        for(auto&e:pairs){e.d=A[e.u]^A[e.v];e.fixed=.65*__builtin_popcountll(e.d>>c.G)+.04*__builtin_popcountll(e.d);}
    }
    void run(int iterations){''')
s=s.replace('''            const auto saved=state;auto windows=choose_windows(t);u64 removed=0;for(int j:windows)removed|=1ULL<<j;''','''            const auto saved=state;auto windows=choose_windows(t);
            int swap_j=-1,swap_h=-1;
            if(t%4==3){swap_j=windows[rng.mod(windows.size())];swap_h=c.G+rng.mod(63-c.G);exchange_coordinate(swap_j,swap_h);}
            u64 removed=0;for(int j:windows)removed|=1ULL<<j;''')
s=s.replace('''++accepted;multi_accepted+=changes>=2;
            }else restore(saved);''','''++accepted;multi_accepted+=changes>=2;window_swaps+=swap_j>=0;
            }else {restore(saved);if(swap_j>=0)exchange_coordinate(swap_j,swap_h);}''')
s=s.replace('''<<"\\ndecoder_nonlinear = "<<nonlinear''','''<<"\\ndecoder_window_swaps = "<<window_swaps<<"\\ndecoder_nonlinear = "<<nonlinear''')
s=s.replace('AtomicGateSearch search(comp, A, env_int("GATE_COMPARATORS"));','AtomicGateSearch search(comp, A, permutation, env_int("GATE_COMPARATORS"));')
(p/'joint.cpp').write_text(s)
