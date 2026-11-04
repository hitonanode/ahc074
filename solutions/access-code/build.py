from pathlib import Path
root=Path(__file__).resolve().parent
source=(root.parent/"patch-code/exact.cpp").read_text().split("int main(int argc,char** argv)")[0]
source=source.replace('#include "probe.cpp"','#include "../patch-code/probe.cpp"')
source=source.replace('opaque[6]=opaque[7]=mask;black[6]=color&mask;black[7]=mask^black[6];','opaque[6]=opaque[7]=mask|kCapBit;black[6]=color&mask;black[7]=(mask^black[6])|kCapBit;')
source+=r'''
int main(int argc,char** argv) {
    if(argc<5)return 2;auto started=elapsed_sec();
    patch_code::Model m;if(!m.load(argv[1],argv[2]))return 3;
    std::ifstream raw(argv[1]);int n,k,p,r;raw>>n>>k>>p>>r;std::string line;
    for(int a=0;a<256;a++){raw>>line;if(line[63]=='1')m.A[a]|=kCapBit;}
    u64 mask=std::stoull(argv[3]),color=std::stoull(argv[4]);int threads=argc>5?std::stoi(argv[5]):4;
    Layer layer(m.comp,mask,color);
    std::array<std::array<double,256>,256> old_cost{},new_cost{},home_cost{},cycle_cost{};
    for(auto& row:old_cost)row.fill(-1);for(auto& row:new_cost)row.fill(-1);for(auto& row:home_cost)row.fill(-1);for(auto& row:cycle_cost)row.fill(-1);
    std::vector<std::pair<int,int>> jobs;int old_pairs=0;
    for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){
        auto reach=m.comp.closure(m.A[a],m.A[a]^m.A[b]);bool ok=true;u64 key=0;
        for(int x=0;x<6;x++){ok&=!(reach[x]>>x&1);key|=u64(reach[x])<<(8*x);}
        if(ok){old_cost[a][b]=old_cost[b][a]=PosetSums::get().both_of(key)/1440.0;old_pairs++;}
        if(ok||__builtin_popcountll((m.A[a]^m.A[b])&~kCapBit)<=26)jobs.emplace_back(a,b);
    }
    std::atomic<int> next{0},novel{0},valid{0};std::vector<std::thread> workers;
    for(int thread=0;thread<threads;thread++)workers.emplace_back([&]{
        Layer::Workspace work(layer.orders.size());
        while(true){int id=next.fetch_add(1);if(id>=int(jobs.size()))break;auto[a,b]=jobs[id];double home,cycle;
            double cost=layer.price(m.A[a],m.A[b],(m.A[a]^m.A[b])&(low_bits(m.G)|kCapBit),work,home,cycle,true);
            if(cost<0)continue;valid++;novel+=old_cost[a][b]<0;
            new_cost[a][b]=new_cost[b][a]=cost;home_cost[a][b]=home_cost[b][a]=home;cycle_cost[a][b]=cycle_cost[b][a]=cycle;
        }
    });
    for(auto& thread:workers)thread.join();
    std::cerr<<"table "<<elapsed_sec()-started<<" pairs "<<valid<<" novel "<<novel<<" visible "<<layer.mean_visible<<'\n';
    std::vector<u64> A=m.A;for(auto& a:A)a&=~kCapBit;
    std::unordered_map<u64,int> index;for(int a=0;a<256;a++)index[A[a]]=a;
    std::cout<<std::setprecision(12)<<"{\"mask\":"<<mask<<",\"color\":"<<color<<",\"table_sec\":"<<elapsed_sec()-started<<",\"old_pairs\":"<<old_pairs<<",\"pairs\":"<<valid<<",\"novel_pairs\":"<<novel<<",\"models\":[";
    for(int variant=0;variant<4;variant++){
        Design d(A,variant?7:6,m.G);
        auto cost=[&](u64 a,u64 b){int x=index[a],y=index[b];return variant==3?cycle_cost[x][y]:variant==2?home_cost[x][y]:variant==1?new_cost[x][y]:old_cost[x][y];};
        if(!d.initialize([&](u64 a,u64 b){return cost(a,b)>=0;},cost,[]{return false;})){std::cout<<(variant?",":"")<<"{\"variant\":"<<variant<<",\"failed\":true}";continue;}
        d.anneal(1e9,20000000);d.filler_climb(1e9,60000);
        double columns=0,holes=0,generic=0,fee=0;int chosen=0;
        for(int c=0;c<d.H;c++){columns+=d.colcost(c);holes+=d.hcost(c);}
        for(auto u:d.unit){generic+=d.gc(u);if(u.b>=0&&old_cost[u.a][u.b]<0){chosen++;fee+=cost(A[u.a],A[u.b]);}}
        if(const char* prefix=std::getenv("ACCESS_SAVE_PREFIX");prefix&&variant){
            std::string name=std::string(prefix)+"-"+std::to_string(variant);
            std::ofstream input(name+".in"),output(name+".out");input<<"64 193 256 1024\n";
            auto text=[](u64 op,u64 black){std::string row(64,'.');for(int j=0;j<64;j++)if(op>>j&1)row[j]=char('0'+((black>>j)&1));return row;};
            for(u64 a:m.A)input<<text(~0ULL,a)<<'\n';
            // A dummy transparent sheet makes this research file readable by
            // generic-mdp's cap + M generic sheets input adapter. K=193 here
            // is solely an analysis container, never an official output.
            output<<std::string(64,'.')<<'\n';
            for(int x=0;x<6;x++)output<<text(m.comp.opq[x],m.comp.black[x])<<'\n';
            output<<text(mask|kCapBit,color&mask)<<'\n'<<text(mask|kCapBit,(mask^color)|kCapBit)<<'\n';
            for(auto u:d.unit){u64 op=low_bits(m.G)|kCapBit;for(int c=0;c<=u.c;c++)op|=1ULL<<d.handle[c];if(u.b>=0)op&=~(m.A[u.a]^m.A[u.b]);output<<text(op,m.A[u.a]&op)<<'\n';}
        }
        std::cout<<(variant?",":"")<<"{\"variant\":"<<variant<<",\"cost\":"<<(columns+holes+generic)/256<<",\"column\":"<<columns/256<<",\"holes\":"<<holes/256<<",\"generic\":"<<generic/256<<",\"novel\":"<<chosen<<",\"novel_fee\":"<<(chosen?fee/chosen:0)<<"}"<<std::flush;
    }
    std::cout<<"],\"elapsed\":"<<elapsed_sec()-started<<"}\n";
}
'''
(root/"cap.cpp").write_text(source)
independent=source.replace('Layer(const Comparator& comp,u64 mask,u64 color)', 'Layer(const Comparator& comp,u64 mask,u64 color,u64 mask1,u64 color1)')
independent=independent.replace('opaque[6]=opaque[7]=mask|kCapBit;black[6]=color&mask;black[7]=(mask^black[6])|kCapBit;', 'opaque[6]=mask|kCapBit;opaque[7]=mask1|kCapBit;black[6]=color&mask;black[7]=(color1&mask1)|kCapBit;')
independent=independent.replace('if(argc<5)return 2;', 'if(argc<7)return 2;')
independent=independent.replace('int threads=argc>5?std::stoi(argv[5]):4;', 'u64 mask1=std::stoull(argv[5]),color1=std::stoull(argv[6]);int threads=argc>7?std::stoi(argv[7]):4;')
independent=independent.replace('Layer layer(m.comp,mask,color);', 'Layer layer(m.comp,mask,color,mask1,color1);')
independent=independent.replace("text(mask|kCapBit,(mask^color)|kCapBit)","text(mask1|kCapBit,(color1&mask1)|kCapBit)")
(root/"independent.cpp").write_text(independent)
