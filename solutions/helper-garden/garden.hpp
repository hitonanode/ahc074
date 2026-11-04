// Price the choice of a helper jointly with the generic state and its access
// cost. The six helpers have only their own handle, so their compatibility
// does not depend on the eventual (deeper) column of the shared paper.
struct Garden {
    Solver& s;
    Design& d;
    std::vector<int> helper;
    std::vector<u64> display;
    std::vector<std::array<u64,7>> prefix;
    std::vector<std::vector<int>> reverse;
    int new_pairs=0;
    explicit Garden(Solver& solver,Design& design):s(solver),d(design){
        s.comparator.build_tables();
        int n=s.comparator.perms.size();display.resize(n);prefix.resize(n);reverse.resize(n);
        for(int i=0;i<n;i++){
            u64 covered=0;
            for(int j=0;j<6;j++){
                int k=s.comparator.perms[i][j];display[i]|=s.paper[k].black&~covered&s.gmask;
                covered|=s.paper[k].opaque&s.gmask;prefix[i][j+1]=covered;
            }
            for(int j:s.comparator.next[i])if(j>=0)reverse[j].push_back(i);
        }
    }
    u64 residue(u64 target,u64 holes)const{
        // Repeatedly expose any generic sheet whose visible part is correct.
        // The remaining bits must all be supplied by the helper; this is an
        // exact existence test for one fully opaque generic helper.
        for(int it=0;it<6;it++){
            u64 next=holes;
            for(int k=0;k<6;k++)if(!((s.paper[k].black^target)&s.paper[k].opaque&holes))next&=~s.paper[k].opaque;
            if(next==holes)break;holes=next;
        }
        return holes;
    }
    void select(int variant){
        d.garden_columns=3;std::mt19937_64 random(871300021ULL*(variant+1));
        if(variant>=2){
            struct Pair{int a,b;u64 ra,rb;double weight;};std::vector<Pair> pairs;
            for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(!d.ok[a][b]){
                u64 diff=s.A[a]^s.A[b];int distance=__builtin_popcountll(diff&kActiveWindows);if(distance>26)continue;
                pairs.push_back({a,b,residue(s.A[a],diff&s.gmask),residue(s.A[b],diff&s.gmask),double(30-distance)});
            }
            std::array<std::vector<int>,6> choices;
            std::array<std::vector<std::vector<uint8_t>>,6> support;
            for(int slot=0;slot<6;slot++){
                int c=slot/2,color=slot%2;
                for(auto u:d.unit)if(u.b<0&&d.color(u,c)==color)choices[slot].push_back(u.a);
                for(int h:choices[slot]){
                    std::vector<uint8_t> v;
                    for(auto p:pairs){
                        u64 handle_hole=(s.A[p.a]^s.A[p.b])&(1ULL<<d.handle[c]);
                        int bits=0;if(h!=p.a&&h!=p.b){
                            if(!((s.A[h]^s.A[p.a])&(p.ra|handle_hole)))bits|=1;
                            if(!((s.A[h]^s.A[p.b])&(p.rb|handle_hole)))bits|=2;
                        }
                        v.push_back(bits);
                    }
                    support[slot].push_back(std::move(v));
                }
            }
            std::array<int,6> chosen{},best;
            std::vector<std::array<int,2>> counts(pairs.size());
            std::array<bool,P> used{};
            for(int slot=0;slot<6;slot++){
                int i=random()%choices[slot].size();while(used[choices[slot][i]])i=(i+1)%choices[slot].size();
                chosen[slot]=i;used[choices[slot][i]]=true;
                for(int p=0;p<int(pairs.size());p++){int z=support[slot][i][p];counts[p][0]+=z&1;counts[p][1]+=(z>>1)&1;}
            }
            auto gain=[](int a,int b){return double(a>0&&b>0)+.05*((a>0)+(b>0));};
            double current=0;for(int p=0;p<int(pairs.size());p++)current+=pairs[p].weight*gain(counts[p][0],counts[p][1]);
            double best_value=current;best=chosen;
            for(int it=0;it<30000;it++){
                int slot=random()%6,next=random()%choices[slot].size(),old=chosen[slot];
                if(used[choices[slot][next]])continue;
                double delta=0;
                for(int p=0;p<int(pairs.size());p++){
                    int a=counts[p][0],b=counts[p][1],x=support[slot][old][p],y=support[slot][next][p];
                    delta+=pairs[p].weight*(gain(a-(x&1)+(y&1),b-((x>>1)&1)+((y>>1)&1))-gain(a,b));
                }
                double temperature=2*std::pow(.01,double(it)/30000);
                if(delta>=0||(random()>>11)*0x1.0p-53<std::exp(delta/temperature)){
                    for(int p=0;p<int(pairs.size());p++){
                        int x=support[slot][old][p],y=support[slot][next][p];counts[p][0]+=(y&1)-(x&1);counts[p][1]+=((y>>1)&1)-((x>>1)&1);
                    }
                    used[choices[slot][old]]=false;used[choices[slot][next]]=true;chosen[slot]=next;current+=delta;
                    if(current>best_value)best_value=current,best=chosen;
                }
            }
            for(int slot=0;slot<6;slot++){int h=choices[slot][best[slot]];helper.push_back(h);d.fixed_helper[h]=slot/2;}
        } else {
        for(int c=0;c<3;c++)for(int b=0;b<2;b++){
            int chosen=-1;double best=1e100;
            for(int x=0;x<d.U;x++){
                auto u=d.unit[x];if(u.b>=0||d.fixed_helper[u.a]>=0||d.color(u,c)!=b)continue;
                // Prefer papers already shallow; random variants explore
                // different generic patterns without using order information.
                double price=.15*u.c+(random()>>11)*0x1.0p-53;
                if(price<best)best=price,chosen=x;
            }
            assert(chosen>=0);helper.push_back(d.unit[chosen].a);d.fixed_helper[d.unit[chosen].a]=c;
        }
        }
        std::vector<int> displaced;
        for(int x=0;x<d.U;x++){
            auto&u=d.unit[x];if(d.fixed_helper[u.a]>=0)u.c=d.fixed_helper[u.a];
            else if(u.c<3){u.c=3;displaced.push_back(x);}
        }
        d.rebuild();d.refresh_reset();
        // Greedily seed a feasible layout; the subsequent annealing can
        // change every other paper's column and sharing partner.
        for(int x:displaced){
            auto old=d.unit[x];d.update(old,-1);double best=1e100;int chosen=-1;
            for(int c=3;c<d.H;c++)if(d.valid(old,c)){
                auto next=old;next.c=c;d.update(next,1);
                if(d.cur<best)best=d.cur,chosen=c;d.update(next,-1);
            }
            assert(chosen>=0);d.unit[x].c=chosen;d.update(d.unit[x],1);
        }
        d.rebuild();d.refresh_reset();
    }
    std::vector<int> distances(int a,int b,int h)const{
        int n=display.size();std::vector<int> dist(n,100),queue;queue.reserve(n);
        u64 holes=(s.A[a]^s.A[b])&s.gmask;
        for(int i=0;i<n;i++){
            if(h<0){if(!((display[i]^s.A[a])&holes))dist[i]=0,queue.push_back(i);}
            else for(int t=6;t>=0;t--){
                u64 view=(display[i]&prefix[i][t])|(s.A[h]&s.gmask&~prefix[i][t]);
                if(!((view^s.A[a])&holes)){dist[i]=0;queue.push_back(i);break;}
            }
        }
        for(int at=0;at<int(queue.size());at++)for(int j:reverse[queue[at]])if(dist[j]==100){dist[j]=dist[queue[at]]+1;queue.push_back(j);}
        return dist;
    }
    double price(int a,int b,bool ordinary)const{
        const int n=display.size();
        std::vector<std::vector<int>> table;
        std::vector<std::pair<int,int>> access;
        if(ordinary)table.push_back(distances(a,b,-1)),access.push_back({-1,0});
        for(int h:helper){
            int c=d.fixed_helper[h];u64 own=1ULL<<d.handle[c];
            if((s.A[h]^s.A[a])&(s.A[a]^s.A[b])&own)continue;
            if((s.A[h]^s.A[a])&residue(s.A[a],(s.A[a]^s.A[b])&s.gmask))continue;
            auto v=distances(a,b,h);assert(v[0]<100);
            table.push_back(std::move(v));access.push_back({c,int(s.A[h]>>d.handle[c]&1)});
        }
        if(table.empty())return 100;
        double result=0;
        for(int state=0;state<n;state++)for(int colors=0;colors<8;colors++){
            double best=100;
            for(int t=0;t<int(table.size());t++){
                auto[c,b]=access[t];double value=table[t][state];
                if(c>=0)value+=1.6+(int(colors>>c&1)!=b);
                best=std::min(best,value);
            }
            result+=best;
        }
        return result/(8*n);
    }
    void build(){
        auto original=d.ok;
        for(auto&v:d.partners)v.clear();for(auto&v:d.ok)v.fill(0);
        for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
            if(d.fixed_helper[a]>=0||d.fixed_helper[b]>=0)continue;
            if(!original[a][b]&&__builtin_popcountll((s.A[a]^s.A[b])&kActiveWindows)>26)continue;
            double p=(price(a,b,original[a][b])+price(b,a,original[a][b]))*.5;
            if(p>=20)continue;
            d.ok[a][b]=d.ok[b][a]=1;d.gcost[a][b]=d.gcost[b][a]=p;
            d.partners[a].push_back(b);d.partners[b].push_back(a);new_pairs+=!original[a][b];
        }
        d.rebuild();d.refresh_reset();
    }
};
