    int expansion_mode = 0;
    long long expanded_total = 0, expanded_selected = 0;
    // Research-only extra end states: change the anchor of a move already in a legal plan.
    // Every edit is replayed from the real initial state; visibility and the full display are
    // checked, so a deep column paper can stay above a shallower column only when it is legal.
    void expand_plans(const State& initial, const EndPlan& base, int u) {
        struct Edit { int k, anchor; };
        std::vector<Edit> edits;
        std::vector<int> ord = initial.order;
        for (auto [k,d] : base.path) {
            ord.erase(std::find(ord.begin(),ord.end(),k));
            edits.push_back({k,d ? ord[d-1] : -1});
            ord.insert(ord.begin()+d,k);
        }
        std::array<bool,K> extra{};
        if(initial.top_d>=0) extra[initial.top_d]=true;
        for(auto f:initial.fillers) extra[f.paper]=true;
        const auto restore_to=save();
        const auto oldops=ops;
        const size_t n0=endplans.size();
        for(int i=0;i<int(edits.size());i++) {
            const int k=edits[i].k,c=col_of[k];
            if(c<0 || k==ded[u])continue;
            ord=initial.order;
            for(int t=0;t<i;t++) {
                auto [x,a]=edits[t];
                ord.erase(std::find(ord.begin(),ord.end(),x));
                const int d=a<0?0:std::find(ord.begin(),ord.end(),a)-ord.begin()+1;
                ord.insert(ord.begin()+d,x);
            }
            std::vector<int> anchors;
            auto add=[&](int a){
                if(a!=k && a!=edits[i].anchor && std::find(anchors.begin(),anchors.end(),a)==anchors.end()) anchors.push_back(a);
            };
            int previous=-1;
            std::array<int,64> rank{};
            for(int x:ord) {
                const int cc=col_of[x];
                if(x==k)continue;
                // All gaps of this column; the first three gaps in either adjacent column.
                // For old out-of-column papers also consider every shallower column boundary.
                if(cc>=0) {
                    if(cc==c || (std::abs(cc-c)==1 && rank[cc]<3)) add(previous),add(x);
                    if(extra[k] && cc<c && !rank[cc])add(previous);
                    rank[cc]++;
                }
                if(extra[k] && x<M)add(x);
                previous=x;
            }
            for(int anchor:anchors) {
                auto trial=edits;
                trial[i].anchor=anchor;
                std::vector<std::pair<int,int>> path;
                ord=initial.order;
                bool ok=true;
                for(auto [x,a]:trial) {
                    if(x==a){ok=false;break;}
                    int pos=std::find(ord.begin(),ord.end(),x)-ord.begin();
                    int to=a<0?0:std::find(ord.begin(),ord.end(),a)-ord.begin()+1;
                    if(pos<to)to--;
                    if(pos==to)continue;
                    u64 cov=0;
                    for(int j=0;j<pos;j++)cov|=paper[ord[j]].opaque;
                    if(!(paper[x].opaque&~cov)){ok=false;break;}
                    ord.erase(ord.begin()+pos);
                    ord.insert(ord.begin()+to,x);
                    path.push_back({x,to});
                }
                if(!ok)continue;
                auto cp=std::find(ord.begin(),ord.end(),kCapPaper);
                for(auto it=ord.begin();it!=cp;it++)if(*it<M)ok=false;
                if(!ok)continue;
                restore(base.state);
                order=ord;
                canonicalize();
                if(display()!=A[u] || !fillers_reachable())continue;
                ops=std::move(path);
                collecting=true;
                collect_plan();
                collecting=false;
            }
        }
        expanded_total+=endplans.size()-n0;
        ops=oldops;
        restore(restore_to);
    }
