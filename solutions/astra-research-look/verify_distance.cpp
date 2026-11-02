#define main submission_main
#include "main.cpp"
#undef main

int main() {
    std::mt19937_64 random(82301917);
    Comparator comp;comp.init(7,21,random);comp.build_tables();
    long long compared=0,path_moves=0;
    constexpr int sources=64;
    for(int trial=0;trial<sources;trial++) {
        int source=trial?random()%5040:0;
        std::vector<int> queue(5040),ds(5040,255);int head=0,tail=0;
        ds[source]=0;queue[tail++]=source;
        while(head<tail) {
            int s=queue[head++];
            for(int t:comp.next[s])if(t>=0&&ds[t]==255)ds[t]=ds[s]+1,queue[tail++]=t;
        }
        assert(tail==5040);
        for(int target=0;target<5040;target++) {
            if(comp.distance(source,target)!=ds[target]) {
                std::cerr<<"distance mismatch "<<source<<' '<<target<<'\n';return 1;
            }
            compared++;
        }
        for(int i=0;i<32;i++) {
            int target=random()%5040;auto p=comp.perms[source];
            auto path=comp.path(source,target);assert(int(path.size())==ds[target]);
            for(auto[k,d]:path) {
                u64 cover=0;bool visible=false;
                for(int x:p) {if(x==k){visible=bool(comp.opq[x]&~cover);break;}cover|=comp.opq[x];}
                if(!visible){std::cerr<<"invisible move\n";return 1;}
                p.erase(std::find(p.begin(),p.end(),k));p.insert(p.begin()+d,k);path_moves++;
            }
            if(p!=comp.perms[target]){std::cerr<<"wrong destination\n";return 1;}
        }
    }
    std::cout<<"source_orders = "<<sources<<"\ncompared_directed_distances = "<<compared
             <<"\nverified_paths = "<<(sources*32)<<"\nlegal_path_moves = "<<path_moves
             <<"\ndistance_mismatches = 0\nvisibility_errors = 0\n";
}
