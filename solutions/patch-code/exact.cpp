#define PATCH_CODE_NO_MAIN
#include "probe.cpp"
#include <atomic>
#include <thread>
#include <unordered_map>

struct Layer {
    using Order=std::array<unsigned char,8>;
    std::vector<Order> orders;
    std::vector<u64> display;
    std::vector<int> begin,reverse;
    std::vector<int> home;
    std::vector<unsigned char> reset_distance;
    std::array<int,256> pc{};
    double mean_visible=0;
    int rank(const Order& p) const {
        int r=0,unused=255;
        for(int i=0;i<8;i++){r=r*(8-i)+pc[unused&((1<<p[i])-1)];unused^=1<<p[i];}return r;
    }
    Layer(const Comparator& comp,u64 mask,u64 color) {
        for(int i=0;i<256;i++)pc[i]=__builtin_popcount(unsigned(i));
        std::array<u64,8> opaque{},black{};
        for(int i=0;i<6;i++){opaque[i]=comp.opq[i];black[i]=comp.black[i];}
        opaque[6]=opaque[7]=mask;black[6]=color&mask;black[7]=mask^black[6];
        Order p{0,1,2,3,4,5,6,7};do{orders.push_back(p);}while(std::next_permutation(p.begin(),p.end()));
        int n=orders.size();display.resize(n);std::vector<std::vector<int>> back(n);
        for(int s=0;s<n;s++) {
            if(orders[s][6]>=6&&orders[s][7]>=6)home.push_back(s);
            u64 covered=0;unsigned visible=0;
            for(int x:orders[s]){u64 seen=opaque[x]&~covered;if(seen)visible|=1U<<x;display[s]|=black[x]&seen;covered|=opaque[x];}
            mean_visible+=__builtin_popcount(visible);
            for(int a=0;a<8;a++)if(visible>>orders[s][a]&1)for(int d=0;d<8;d++)if(a!=d) {
                Order q=orders[s];int x=q[a];
                if(a<d)for(int j=a;j<d;j++)q[j]=q[j+1];
                else for(int j=a;j>d;j--)q[j]=q[j-1];
                q[d]=x;back[rank(q)].push_back(s);
            }
        }
        mean_visible/=n;begin.resize(n+1);
        for(int s=0;s<n;s++)begin[s+1]=begin[s]+back[s].size();
        reverse.resize(begin[n]);for(int s=0;s<n;s++)std::copy(back[s].begin(),back[s].end(),reverse.begin()+begin[s]);
        reset_distance.assign(n,255);std::vector<int> queue=home;
        for(int s:home)reset_distance[s]=0;
        for(int front=0;front<int(queue.size());front++) {
            int s=queue[front];for(int j=begin[s];j<begin[s+1];j++) {
                int t=reverse[j];if(reset_distance[t]!=255)continue;
                reset_distance[t]=reset_distance[s]+1;queue.push_back(t);
            }
        }
        assert(int(queue.size())==n);
    }
    struct Workspace {std::array<std::vector<unsigned char>,2> dist;std::array<std::vector<int>,2> queue;Workspace(int n){for(int z=0;z<2;z++){dist[z].resize(n);queue[z].resize(n);}}};
    double price(u64 a,u64 b,u64 holes,Workspace& w,double& home_price,double& cycle_price,bool cycle) const {
        int n=orders.size();std::array<int,2> end{};
        for(int z=0;z<2;z++)std::fill(w.dist[z].begin(),w.dist[z].end(),255);
        for(int s=0;s<n;s++) {
            if(!((display[s]^a)&holes)){w.dist[0][s]=0;w.queue[0][end[0]++]=s;}
            if(!((display[s]^b)&holes)){w.dist[1][s]=0;w.queue[1][end[1]++]=s;}
        }
        if(!end[0]||!end[1])return -1;
        long long sum=0;
        long long home_sum=0,cycle_sum=0;
        for(int z=0;z<2;z++) {
            auto& d=w.dist[z];auto& q=w.queue[z];
            for(int front=0;front<end[z];front++) {
                int s=q[front],distance=d[s]+1;
                for(int j=begin[s];j<begin[s+1];j++) {
                    int t=reverse[j];if(d[t]!=255)continue;d[t]=distance;sum+=distance;q[end[z]++]=t;
                }
            }
            if(end[z]!=n)return -2;
            for(int s:home)home_sum+=d[s];
            if(cycle) {
                // A complete excursion: show the requested pattern, then return
                // both patches below the six comparator sheets. The return can
                // be performed at the next request, before its normal handling.
                std::array<std::vector<int>,64> buckets;
                u64 target=z?b:a;
                std::fill(d.begin(),d.end(),255);
                for(int s=0;s<n;s++)if(!((display[s]^target)&holes)) {
                    d[s]=reset_distance[s];buckets[d[s]].push_back(s);
                }
                for(int level=0;level<63;level++)for(int s:buckets[level])if(d[s]==level) {
                    for(int j=begin[s];j<begin[s+1];j++) {
                        int t=reverse[j];if(d[t]<=level+1)continue;
                        d[t]=level+1;buckets[level+1].push_back(t);
                    }
                }
                for(int s:home)cycle_sum+=d[s];
            }
        }
        home_price=double(home_sum)/(2*home.size());cycle_price=cycle?double(cycle_sum)/(2*home.size()):home_price;
        return double(sum)/(2*n);
    }
};

int main(int argc,char** argv) {
    if(argc<5)return 2;using Clock=std::chrono::steady_clock;auto t0=Clock::now();
    patch_code::Model m;if(!m.load(argv[1],argv[2]))return 3;
    u64 mask=std::stoull(argv[3]),color=std::stoull(argv[4]);
    int threads=argc>5?std::stoi(argv[5]):4;
    Layer layer(m.comp,mask,color);
    std::array<std::array<double,256>,256> old_cost{},new_cost{},home_cost{},cycle_cost{};
    for(auto& r:old_cost)r.fill(-1);for(auto& r:new_cost)r.fill(-1);for(auto& r:home_cost)r.fill(-1);for(auto& r:cycle_cost)r.fill(-1);
    std::array<std::array<int,256>,256> near_id{};for(auto& r:near_id)r.fill(-1);
    for(int i=0;i<int(m.pairs.size());i++){auto& p=m.pairs[i];near_id[p.a][p.b]=i;}
    std::vector<std::pair<int,int>> jobs;
    int old_pairs=0,novel_pairs=0;
    for(int a=0;a<256;a++)for(int b=a+1;b<256;b++) {
        auto reach=m.comp.closure(m.A[a],m.A[a]^m.A[b]);bool ok=true;u64 key=0;
        for(int x=0;x<6;x++){ok&=!(reach[x]>>x&1);key|=u64(reach[x])<<(8*x);}
        if(ok){old_cost[a][b]=old_cost[b][a]=PosetSums::get().both_of(key)/1440.0;old_pairs++;}
        bool possible=ok;int id=near_id[a][b];if(id>=0)possible|=m.accepts(m.pairs[id],mask,color);
        if(possible){jobs.emplace_back(a,b);novel_pairs+=!ok;}
    }
    std::cerr<<"eligible "<<jobs.size()<<" old "<<old_pairs<<" novel "<<novel_pairs<<" visible "<<layer.mean_visible<<'\n';
    std::atomic<int> next{0},failed{0};std::vector<std::thread> workers;
    for(int thread=0;thread<threads;thread++)workers.emplace_back([&] {
        Layer::Workspace w(layer.orders.size());
        while(true){int id=next.fetch_add(1);if(id>=int(jobs.size()))break;auto[a,b]=jobs[id];double home,cycle;double c=layer.price(m.A[a],m.A[b],(m.A[a]^m.A[b])&low_bits(m.G),w,home,cycle,old_cost[a][b]<0);if(c<0)failed++;new_cost[a][b]=new_cost[b][a]=c;home_cost[a][b]=home_cost[b][a]=old_cost[a][b]>=0?old_cost[a][b]:home;cycle_cost[a][b]=cycle_cost[b][a]=old_cost[a][b]>=0?old_cost[a][b]:cycle;}
    });
    for(auto& w:workers)w.join();if(failed){std::cerr<<"failed "<<failed<<'\n';return 4;}
    double table_sec=std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE;
    std::unordered_map<u64,int> index;for(int a=0;a<256;a++)index[m.A[a]]=a;
    std::cout<<std::setprecision(10)<<"{\"table_sec\":"<<table_sec<<",\"old_pairs\":"<<old_pairs<<",\"novel_pairs\":"<<novel_pairs<<",\"mean_visible\":"<<layer.mean_visible<<",\"models\":[";
    for(int variant=0;variant<4;variant++) {
        Design d(m.A,variant?8:6,m.G);
        auto cost=[&](u64 a,u64 b){int x=index[a],y=index[b];return variant==3?cycle_cost[x][y]:variant==2?home_cost[x][y]:variant==1?new_cost[x][y]:old_cost[x][y];};
        if(!d.initialize([&](u64 a,u64 b){return cost(a,b)>=0;},cost,[]{return false;}))return 5;
        d.anneal(1e9,20000000);d.filler_climb(1e9,60000);
        double retrieval=0,holes=0,generic=0,novel_fee=0;int novel=0;
        for(int c=0;c<d.H;c++){retrieval+=d.colcost(c);holes+=d.hcost(c);}
        for(auto u:d.unit){generic+=d.gc(u);if(u.b>=0&&old_cost[u.a][u.b]<0){novel++;novel_fee+=cost(m.A[u.a],m.A[u.b]);}}
        std::cout<<(variant?",":"")<<"{\"variant\":"<<variant<<",\"cost\":"<<(retrieval+holes+generic)/256<<",\"column\":"<<retrieval/256<<",\"holes\":"<<holes/256<<",\"generic\":"<<generic/256<<",\"novel\":"<<novel<<",\"novel_fee\":"<<(novel?novel_fee/novel:0)<<"}"<<std::flush;
    }
    std::cout<<"],\"elapsed\":"<<std::chrono::duration<double>(Clock::now()-t0).count()*CLOCK_SCALE<<"}\n";
}
