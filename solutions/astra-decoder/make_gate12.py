from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'gates.cpp').read_text()
s=s.replace('''    bool nonlinear = false;''','''    bool nonlinear = false;
    // Search may use only twelve protected comparison witnesses. Final pricing
    // and execution rebuild the graph from the entire actual print pattern.
    bool conservative_graph = false;
    std::vector<u64> graph_opq;
    void reset_graph() {
        perms.clear();next.clear();below.clear();dist.clear();incoming_radius.clear();memo.clear();
    }''')
s=s.replace('''        for (int a = 0; a < n; a++)
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d) {''','''        for (int a = 0; a < n; a++) {
            unsigned visible=0;u64 covered=0;
            const auto& opaque=conservative_graph ? graph_opq : opq;
            for(int pos=0;pos<M;pos++) {int k=perms[a][pos];if(opaque[k]&~covered)visible|=1U<<pos;covered|=opaque[k];}
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d && (visible>>pos&1)) {''')
s=s.replace('''                        next[a][pos * M + d] = int(std::lower_bound(perms.begin(), perms.end(), o2) - perms.begin());
                    }
        dist.assign''','''                        next[a][pos * M + d] = int(std::lower_bound(perms.begin(), perms.end(), o2) - perms.begin());
                    }
        }
        dist.assign''')
s=s.replace('''            if(!seen[x][y])seen[x][y]=true,protected_mask|=1ULL<<j;else movable.push_back(j);''','''            const bool omit = env_int("GATE_WITNESSES")==12 && x%2==0 && y==x+1;
            if(!seen[x][y]&&!omit)protected_mask|=1ULL<<j;else movable.push_back(j);
            seen[x][y]=true;''')
s=s.replace('''    void run(int iterations){
        const u64 gm''','''    void run(int iterations){
        c.conservative_graph=true;c.graph_opq.resize(6);
        for(int k=0;k<6;k++)c.graph_opq[k]=c.opq[k]&protected_mask;
        c.reset_graph();c.rebuild_truth();
        const u64 gm''')
s=s.replace('''        c.rebuild_truth();int nonlinear=0;''','''        // Final exact graph includes extra visibility from all learned gates.
        c.conservative_graph=false;c.reset_graph();c.rebuild_truth();
        int nonlinear=0;''')
(p/'gates12.cpp').write_text(s)
