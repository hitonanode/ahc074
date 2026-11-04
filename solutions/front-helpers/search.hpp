#include <unordered_map>

struct WeaveSearch {
    std::array<int,4> excluded={-1,-1,-1,-1};
    std::array<int,2> helpers={-1,-1};
    bool excluded_unit(int k)const{return std::find(excluded.begin(),excluded.end(),k)!=excluded.end();}
    bool helper_unit(int k)const{return k==helpers[0]||k==helpers[1];}
    Solver& s;
    Design& d;
    std::vector<u64> shown;
    std::vector<std::array<u64, 7>> prefix;
    std::vector<std::vector<int>> reverse;
    std::unordered_map<unsigned, double> generic_cache;
    std::vector<double> black_probability, base_rank, extra_rank;
    int near = 0, rescued = 0, replacements = 0;
    struct Result {
        double delta = 1e100;
        int x=-1,y=-1,z=-1,ha=-1,hb=-1;
        std::array<Design::Unit,3> unit;
    };
    explicit WeaveSearch(Solver& solver, Design& design) : s(solver), d(design) {
        s.comparator.build_tables();
        const int n=s.comparator.perms.size();
        shown.resize(n);prefix.resize(n);reverse.resize(n);
        for(int i=0;i<n;i++){
            u64 covered=0;
            for(int j=0;j<6;j++){
                int k=s.comparator.perms[i][j];
                shown[i]|=s.paper[k].black&~covered&s.gmask;
                covered|=s.paper[k].opaque&s.gmask;prefix[i][j+1]=covered;
            }
            for(int j:s.comparator.next[i])if(j>=0)reverse[j].push_back(i);
        }
        black_probability.resize(d.H);base_rank.resize(d.H);extra_rank.resize(d.U);
        for(int c=0;c<d.H;c++){
            double x=d.hn[c][0],y=d.hn[c][1],t=2*d.nt[c];
            black_probability[c]=(y+t*(y>x))/std::max(1.,x+y+t);
        }
        for(int c=0;c<d.H;c++)base_rank[c]=rank_cost(c,-1,-1);
        for(int k=0;k<d.U;k++)extra_rank[k]=rank_cost(d.unit[k].c,k,-1)-base_rank[d.unit[k].c];
    }
    u64 residue(u64 target,u64 holes)const{
        std::array<unsigned,6> pred{};
        for(u64 z=holes&s.gmask;z;z&=z-1){int j=__builtin_ctzll(z);auto[a,b]=s.comparator.edge[j];if(int(target>>j&1)!=s.comparator.polarity[j])std::swap(a,b);pred[b]|=1U<<a;}
        unsigned left=63;
        while(true){unsigned remove=0;for(int k=0;k<6;k++)if((left>>k&1)&&!(pred[k]&left))remove|=1U<<k;if(!remove)break;left&=~remove;}
        u64 answer=0;
        for(u64 z=holes&s.gmask;z;z&=z-1){int j=__builtin_ctzll(z);auto[a,b]=s.comparator.edge[j];if((left>>a&1)&&(left>>b&1))answer|=1ULL<<j;}
        return answer;
    }
    double generic_cost(int a,int b,int helper){
        unsigned key=unsigned(a)|(unsigned(b)<<8)|(unsigned(helper)<<16);
        auto found=generic_cache.find(key);if(found!=generic_cache.end())return found->second;
        const auto&paper=s.paper[helper+7];const u64 holes=(s.A[a]^s.A[b])&s.gmask;
        const int n=shown.size();std::vector<int> distance(n,-1),queue;queue.reserve(n);
        for(int i=0;i<n;i++)for(int t=6;t>=0;t--){
            u64 view=(shown[i]&(prefix[i][t]|~paper.opaque))|(paper.black&~prefix[i][t]);
            if(!((view^s.A[a])&holes)){distance[i]=0;queue.push_back(i);break;}
        }
        for(int at=0;at<int(queue.size());at++)for(int j:reverse[queue[at]])if(distance[j]<0){distance[j]=distance[queue[at]]+1;queue.push_back(j);}
        double value=1e6;
        if(int(queue.size())==n)value=double(std::accumulate(distance.begin(),distance.end(),0))/n;
        generic_cache[key]=value;return value;
    }
    double rank_cost(int c,int h1,int h2)const{
        std::array<std::vector<int>,2> weight;
        for(int k=0;k<d.U;k++)if(d.unit[k].c==c)weight[d.color(d.unit[k],c)].push_back(d.weight(d.unit[k])+(k==h1)+(k==h2));
        for(auto&v:weight)std::sort(v.rbegin(),v.rend());
        assert(!weight[0].empty()&&!weight[1].empty());
        std::vector<int> tail;
        for(auto&v:weight)tail.insert(tail.end(),v.begin()+1,v.end());
        std::sort(tail.rbegin(),tail.rend());
        double common=0;for(int j=0;j<int(tail.size());j++)common+=(j+2)*tail[j];
        double p=black_probability[c];
        return common+(1-p)*weight[1][0]+p*weight[0][0];
    }
    double helper_rank(int a,int b)const{
        int ca=d.unit[a].c,cb=d.unit[b].c;
        if(ca==cb)return rank_cost(ca,a,b)-base_rank[ca];
        return extra_rank[a]+extra_rank[b];
    }
    double hole_delta(const std::array<int,4>&targets,const std::array<u64,4>&holes)const{
        auto hn=d.hn;
        for(int i=0;i<4;i++){
            int t=targets[i];if(t<0)continue;u64 old=d.holes(d.unit[d.owner[t]]),add=holes[i]&~old,sub=old&~holes[i];
            for(u64 z=add;z;z&=z-1){int c=__builtin_ctzll(z);hn[c][d.hb[t]>>c&1]++;}
            for(u64 z=sub;z;z&=z-1){int c=__builtin_ctzll(z);hn[c][d.hb[t]>>c&1]--;}
        }
        double cost=0;
        for(int c=0;c<d.H;c++){double x=hn[c][0],y=hn[c][1],t=d.reset_targets[c];cost+=4*Design::kHoleWeight*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t)-d.hcost(c);}
        return cost;
    }
    Result search(){
        Result best;std::vector<int> singles,pairs;
        for(int k=0;k<d.U;k++)if(!excluded_unit(k))(d.unit[k].b<0?singles:pairs).push_back(k);
        for(int yi=0;yi<int(singles.size());yi++)for(int zi=yi+1;zi<int(singles.size());zi++){
            int y=singles[yi],z=singles[zi],a=d.unit[y].a,b=d.unit[z].a;
            const u64 diff=s.A[a]^s.A[b];
            if(__builtin_popcountll(diff&kActiveWindows)>26||d.ok[a][b])continue;
            near++;const u64 ra=residue(s.A[a],diff),rb=residue(s.A[b],diff);
            std::vector<int> ga,gb;
            for(int k=0;k<d.U;k++)if(helper_unit(k)&&k!=y&&k!=z){auto pp=s.paper[k+7];
                if(!((pp.black^s.A[a])&pp.opaque&ra)&&!residue(s.A[a],ra&~pp.opaque))ga.push_back(k);
                if(!((pp.black^s.A[b])&pp.opaque&rb)&&!residue(s.A[b],rb&~pp.opaque))gb.push_back(k);
            }
            if(ga.empty()||gb.empty())continue;
            bool possible=false;
            for(int x:pairs){auto old=d.unit[x];Design::Unit np{a,b,old.c};
                if(!d.valid(np,np.c)||d.color(np,np.c)!=d.color(old,old.c))continue;
                const u64 nh=d.holes(np);u64 physical_holes=0;for(int c=0;c<d.H;c++)if(nh>>c&1)physical_holes|=1ULL<<d.handle[c];
                std::vector<int> ha,hb;
                for(int k:ga)if(k!=x&&d.unit[k].c!=old.c&&!((s.paper[k+7].black^s.A[a])&s.paper[k+7].opaque&physical_holes))ha.push_back(k);
                for(int k:gb)if(k!=x&&d.unit[k].c!=old.c&&!((s.paper[k+7].black^s.A[b])&s.paper[k+7].opaque&physical_holes))hb.push_back(k);
                if(ha.empty()||hb.empty())continue;
                for(int flip=0;flip<2;flip++){
                    Design::Unit ny{flip?old.b:old.a,-1,d.unit[y].c},nz{flip?old.a:old.b,-1,d.unit[z].c};
                    if(d.color(ny,ny.c)!=d.color(d.unit[y],ny.c)||d.color(nz,nz.c)!=d.color(d.unit[z],nz.c))continue;
                    possible=true;
                    for(int aa:ha)for(int bb:hb){
                        replacements++;
                        double price=generic_cost(a,b,aa)+generic_cost(b,a,bb)+3.2-2*d.gcost[old.a][old.b];
                        price+=helper_rank(aa,bb);
                        price+=hole_delta({a,b,ny.a,nz.a},{nh&~s.h_opq[aa+7],nh&~s.h_opq[bb+7],d.holes(ny),d.holes(nz)});
                        if(price<best.delta)best={price,x,y,z,aa,bb,{np,ny,nz}};
                    }
                }
            }
            rescued+=possible;
        }
        // Also exchange one product between two papers. The new partner of
        // the displaced product must remain ordinarily decodable.
        for(int x:pairs)for(int y=0;y<d.U;y++)if(x!=y&&!excluded_unit(y))for(int side=0;side<2;side++)for(int other=0;other<(d.unit[y].b>=0?2:1);other++){
            auto ox=d.unit[x],oy=d.unit[y];
            int a=side?ox.b:ox.a,old=side?ox.a:ox.b,b=other?oy.b:oy.a;
            Design::Unit nx{a,b,ox.c},ny{old,oy.b<0?-1:other?oy.a:oy.b,oy.c};
            if(d.ok[a][b]||__builtin_popcountll((s.A[a]^s.A[b])&kActiveWindows)>26||
                (ny.b>=0&&!d.ok[ny.a][ny.b])||!d.valid(nx,nx.c)||!d.valid(ny,ny.c)||
                d.color(nx,nx.c)!=d.color(ox,ox.c)||d.color(ny,ny.c)!=d.color(oy,oy.c))continue;
            near++;
            u64 diff=s.A[a]^s.A[b],ra=residue(s.A[a],diff),rb=residue(s.A[b],diff),nh=d.holes(nx),physical_holes=0;
            for(int c=0;c<d.H;c++)if(nh>>c&1)physical_holes|=1ULL<<d.handle[c];
            std::vector<int>ha,hb;
            for(int k=0;k<d.U;k++)if(helper_unit(k)&&k!=x&&k!=y&&d.unit[k].c!=nx.c){auto pp=s.paper[k+7];
                if(!((pp.black^s.A[a])&pp.opaque&(ra|physical_holes))&&!residue(s.A[a],ra&~pp.opaque))ha.push_back(k);
                if(!((pp.black^s.A[b])&pp.opaque&(rb|physical_holes))&&!residue(s.A[b],rb&~pp.opaque))hb.push_back(k);
            }
            if(ha.empty()||hb.empty())continue;
            rescued++;
            for(int aa:ha)for(int bb:hb){
                replacements++;
                double price=generic_cost(a,b,aa)+generic_cost(b,a,bb)+3.2+d.gc(ny)-d.gc(ox)-d.gc(oy)+helper_rank(aa,bb);
                price+=hole_delta({a,b,ny.a,ny.b},{nh&~s.h_opq[aa+7],nh&~s.h_opq[bb+7],d.holes(ny),d.holes(ny)});
                if(price<best.delta)best={price,x,y,-1,aa,bb,{nx,ny,Design::Unit{}}};
            }
        }
        return best;
    }
};
