#define main submission_main
#include "main.cpp"
#undef main

int main() {
    std::mt19937_64 random(82301917);
    Comparator comp;comp.init(6,36,random);comp.build_tables();
    long long compared=0;
    for(int source=0;source<720;source++) {
        std::vector<int> queue(720),ds(720,255);int head=0,tail=0;
        ds[source]=0;queue[tail++]=source;
        while(head<tail) {
            int s=queue[head++];
            for(int t:comp.next[s])if(t>=0&&ds[t]==255)ds[t]=ds[s]+1,queue[tail++]=t;
        }
        assert(tail==720);
        for(int target=0;target<720;target++) {
            if(comp.distance(source,target)!=ds[target]) {
                std::cerr<<"distance mismatch "<<source<<' '<<target<<'\n';return 1;
            }
            compared++;
        }
    }
    std::cout<<"source_orders = 720\ncompared_directed_distances = "<<compared<<"\ndistance_mismatches = 0\n";
}
