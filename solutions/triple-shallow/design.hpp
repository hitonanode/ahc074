#include "common.hpp"
#include <bit>
#include <unordered_map>
using U=u64;
struct Problem {
    int M=6,G;U gm;std::vector<U>A;Comparator comp;
    std::array<std::array<unsigned char,256>,256> compatible{};
    std::array<std::array<float,256>,256> gcost{};
    double triple_price;
    Problem(const Design&d,const Comparator&c,bool triples):G(d.G),gm(low_bits(d.G)),A(d.A),comp(c),gcost(d.gcost),triple_price(triples?0:-1){
        for(int a=0;a<256;a++)for(int b=0;b<256;b++)compatible[a][b]=d.ok[a][b];
    }
    double fee(U target,U holes)const{
        auto relation=comp.closure(target,holes);u64 key=0;
        for(int k=0;k<6;k++){if(relation[k]>>k&1)return -1;key|=u64(relation[k])<<(8*k);}
        const auto& table=PosetSums::get();return table.one[table.slot_of(key)]/720.;
    }
};
struct Group {std::array<int,3> a{-1,-1,-1};int n=0;U diff=0;double fee=0;};
struct Search {
    Problem& p;int H,Ucount;std::mt19937_64 rng{94361617};
    std::vector<Group> groups;std::unordered_map<unsigned,int> index;std::vector<int> triples,pairs;
    struct Unit {int group,column;};std::vector<Unit> units;
    std::array<int,256> owner{};std::array<int,64> handles{};
    std::array<std::array<std::array<int,2>,4>,64> counts{};
    std::array<std::array<int,2>,64> holes{};double current=0;
    static unsigned key(std::array<int,3> a,int n){std::sort(a.begin(),a.begin()+n);return unsigned(n)<<24|unsigned(a[0])<<16|(n>1?unsigned(a[1])<<8:0)|(n>2?unsigned(a[2]):0);}
    void add(std::array<int,3> a,int n){
        Group g;g.a=a;g.n=n;for(int t=1;t<n;t++)g.diff|=p.A[a[0]]^p.A[a[t]];
        if(n==2){if(!p.compatible[a[0]][a[1]])return;g.fee=2*p.gcost[a[0]][a[1]];}
        if(n==3)for(int t=0;t<3;t++){double value=p.fee(p.A[a[t]],g.diff);if(value<0)return;g.fee+=value;}
        int id=groups.size();index[key(a,n)]=id;groups.push_back(g);if(n==2)pairs.push_back(id);if(n==3)triples.push_back(id);
    }
    Search(Problem& problem):p(problem),H(63-p.G),Ucount(191-p.M){
        assert(H<=63);for(int j=0;j<H;j++)handles[j]=p.G+j;
        for(int a=0;a<256;a++)add({a,-1,-1},1);
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p.compatible[a][b])add({a,b,-1},2);
        if(p.triple_price>=0)for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p.compatible[a][b])for(int c=b+1;c<256;c++)if(p.compatible[a][c]&&p.compatible[b][c]){
            U d=(p.A[a]^p.A[b])|(p.A[a]^p.A[c]);if(std::popcount(d)<=40)add({a,b,c},3);
        }
    }
    int lookup(std::array<int,3> a,int n)const {auto it=index.find(key(a,n));return it==index.end()?-1:it->second;}
    bool valid(int id,int col)const{return !(groups[id].diff>>handles[col]&1);}
    static double colcost(const std::array<std::array<int,2>,4>& count){
        int n=0,total=0,colors[2]{};for(int w=1;w<=3;w++)for(int b=0;b<2;b++){n+=count[w][b];total+=w*count[w][b];colors[b]+=count[w][b];}
        if(!colors[0]||!colors[1])return 100000;
        double best=1e30;
        for(int first=0;first<2;first++){
            auto copy=count;int rank=0,price=0;
            for(int color:{first,1-first})for(int w=3;w;w--)if(copy[w][color]){copy[w][color]--;price+=w*rank++;break;}
            for(int w=3;w;w--){int k=copy[w][0]+copy[w][1];price+=w*(k*rank+k*(k-1)/2);rank+=k;}
            best=std::min(best,double(price));
        }
        return best;
    }
    std::array<double,64>reset{};
    double holecost(int c)const{double x=holes[c][0],y=holes[c][1],t=reset[c];return 1.6*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);}
    void refresh(){for(int c=0;c<H;c++){reset[c]=0;for(int w=1;w<=3;w++)reset[c]+=2*w*(counts[c][w][0]+counts[c][w][1]);}rebuild();}
    void update(Unit u,int sign){
        const auto& g=groups[u.group];int c=u.column,b=p.A[g.a[0]]>>handles[c]&1;
        current-=colcost(counts[c]);counts[c][g.n][b]+=sign;current+=colcost(counts[c]);
        for(int j=0;j<H;j++)if(j>c||(g.diff>>handles[j]&1)){
            current-=holecost(j);for(int t=0;t<g.n;t++)holes[j][p.A[g.a[t]]>>handles[j]&1]+=sign;current+=holecost(j);
        }
        current+=sign*g.fee;
    }
    void rebuild(){counts={};holes={};current=100000.0*H;for(int i=0;i<Ucount;i++){update(units[i],1);auto g=groups[units[i].group];for(int t=0;t<g.n;t++)owner[g.a[t]]=i;}}
    bool initialize(int requested_triples){
        std::vector<int> ranked=triples;auto price=[&](int id){auto&g=groups[id];return (g.fee+.4*g.n*std::popcount(g.diff&~p.gm)+.04*std::popcount(g.diff))/(g.n-1);};
        std::sort(ranked.begin(),ranked.end(),[&](int a,int b){return price(a)<price(b);});std::array<bool,256>used{};int deficit=256-Ucount;
        for(int id:ranked){if(!requested_triples||deficit<2)break;auto&g=groups[id];if(used[g.a[0]]||used[g.a[1]]||used[g.a[2]])continue;for(int t=0;t<3;t++)used[g.a[t]]=true;units.push_back({id,-1});requested_triples--;deficit-=2;}
        ranked=pairs;std::sort(ranked.begin(),ranked.end(),[&](int a,int b){return price(a)<price(b);});
        for(int id:ranked){if(!deficit)break;auto&g=groups[id];if(used[g.a[0]]||used[g.a[1]])continue;used[g.a[0]]=used[g.a[1]]=true;units.push_back({id,-1});deficit--;}
        while(deficit){bool ok=false;for(auto&u:units){auto g=groups[u.group];if(g.n!=2)continue;for(int a=0;a<256&&!ok;a++)if(!used[a])for(int b=a+1;b<256&&!ok;b++)if(!used[b])for(int f=0;f<2;f++){int x=lookup({g.a[f],a,-1},2),y=lookup({g.a[1-f],b,-1},2);if(x>=0&&y>=0){u.group=x;units.push_back({y,-1});used[a]=used[b]=true;ok=true;break;}}if(ok)break;}if(!ok)return false;deficit--;}
        for(int a=0;a<256;a++)if(!used[a])units.push_back({lookup({a,-1,-1},1),-1});assert(int(units.size())==Ucount);
        std::vector<int> order(Ucount);std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);
        std::array<int,64> nc{},n1{},capacity{};
        auto take=[&](int c,int color,bool shared){for(int pass=0;pass<2;pass++)for(int x:order){auto&u=units[x];auto&g=groups[u.group];if(u.column>=0||((g.n>1)!=(shared^(pass!=0)))||!valid(u.group,c)||(p.A[g.a[0]]>>handles[c]&1)!=color)continue;u.column=c;nc[c]++;n1[c]+=color;return true;}return false;};
        for(int c=0;c<H;c++)for(int b=0;b<2;b++)if(!take(c,b,false))return false;
        for(int c=0;c<H;c++)capacity[c]=2;int total=2*H;
        while(total<Ucount){int best=0;for(int c=1;c<H;c++)if((capacity[c]+1.)/(c+1.5)<(capacity[best]+1.)/(best+1.5))best=c;capacity[best]++;total++;}
        for(int c=H-1;c>=0;c--)while(nc[c]<capacity[c]){int color=2*n1[c]<nc[c];if(!take(c,color,true)&&!take(c,1-color,true))break;}
        for(auto&u:units)if(u.column<0){double best=1e30;int col=-1;for(int c=0;c<H;c++)if(valid(u.group,c)){double value=groups[u.group].n*(nc[c]*.5+.4*(H-1-c))+nc[c]*.5;if(value<best){best=value;col=c;}}if(col<0)return false;u.column=col;nc[col]++;}
        rebuild();return true;
    }
    void optimize(int iterations){
        double best=current;auto best_units=units;auto best_handles=handles;
        for(int it=0;it<iterations;it++){
            if(it%std::max(1,iterations/4)==0){refresh();best=current;best_units=units;best_handles=handles;}
            const double temp=.8*std::pow(.004,double(it)/std::max(1,iterations-1));int kind=rng()%100;double before=current;
            if(kind<4){
                int a=rng()%H,b=rng()%H;if(a==b)continue;bool ok=true;
                for(auto u:units)if((u.column==a&&!valid(u.group,b))||(u.column==b&&!valid(u.group,a))){ok=false;break;}if(!ok)continue;
                std::swap(handles[a],handles[b]);for(auto&u:units){if(u.column==a)u.column=b;else if(u.column==b)u.column=a;}rebuild();
                if(current>before&&std::generate_canonical<double,53>(rng)>=std::exp((before-current)/temp)){std::swap(handles[a],handles[b]);for(auto&u:units){if(u.column==a)u.column=b;else if(u.column==b)u.column=a;}rebuild();}
            }else{
                int x=rng()%Ucount,y=rng()%Ucount;if(x==y)continue;Unit nx=units[x],ny=units[y];
                if(kind<40){if(kind<22)nx.column=rng()%H;else std::swap(nx.column,ny.column);}
                else if(kind<60&&!triples.empty()){
                    int id=triples[rng()%triples.size()];auto&g=groups[id];std::array<int,3> own{owner[g.a[0]],owner[g.a[1]],owner[g.a[2]]};std::sort(own.begin(),own.end());if(own[0]==own[2]||(own[0]!=own[1]&&own[1]!=own[2]))continue;x=own[0];y=own[2];nx=units[x];ny=units[y];std::array<int,3> rest{-1,-1,-1};int n=0;
                    for(int z:{x,y}){auto&old=groups[units[z].group];for(int t=0;t<old.n;t++){int a=old.a[t];if(a!=g.a[0]&&a!=g.a[1]&&a!=g.a[2]){if(n==3){n=4;break;}rest[n++]=a;}}if(n>3)break;}
                    if(n<1||n>3)continue;int other=lookup(rest,n);if(other<0)continue;nx.group=id;ny.group=other;if(rng()&1)std::swap(nx.group,ny.group);
                }else{
                    std::array<int,6> values{};int n=0;for(int z:{x,y}){auto&g=groups[units[z].group];for(int t=0;t<g.n;t++)values[n++]=g.a[t];}std::shuffle(values.begin(),values.begin()+n,rng);int low=std::max(1,n-3),high=std::min(3,n-1),cut=low+rng()%(high-low+1);std::array<int,3>a{-1,-1,-1},b{-1,-1,-1};for(int i=0;i<cut;i++)a[i]=values[i];for(int i=cut;i<n;i++)b[i-cut]=values[i];nx.group=lookup(a,cut);ny.group=lookup(b,n-cut);if(nx.group<0||ny.group<0)continue;
                }
                if(!valid(nx.group,nx.column)||!valid(ny.group,ny.column))continue;
                auto ox=units[x],oy=units[y];update(ox,-1);update(oy,-1);update(nx,1);update(ny,1);
                if(current<=before||std::generate_canonical<double,53>(rng)<std::exp((before-current)/temp)){units[x]=nx;units[y]=ny;for(int z:{x,y}){auto&g=groups[units[z].group];for(int t=0;t<g.n;t++)owner[g.a[t]]=z;}}
                else{update(nx,-1);update(ny,-1);update(ox,1);update(oy,1);}
            }
            if(current<best){best=current;best_units=units;best_handles=handles;}
        }
        units=best_units;handles=best_handles;rebuild();
    }
};
