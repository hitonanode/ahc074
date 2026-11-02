// Independent check of the offline reverse-BFS costs against the online
// maximum-retained-subsequence planner, including every actual move's legality.
#define main submission_main
#include "main.cpp"
#undef main

int main(int argc,char** argv) {
    int first=argc>1?std::atoi(argv[1]):0;
    int last=argc>2?std::atoi(argv[2]):2045;
    Comparator comp;comp.M=7;comp.G=21;
    for(int a=0;a<7;a++)for(int b=a+1;b<7;b++)comp.edge.emplace_back(a,b),comp.polarity.push_back(1);
    comp.rebuild();
    long long checked=0,moves=0;
    for(int c=first;c<last;c++) {
        const u64 r=kPoset7Classes[c].relation;
        u64 holes=0,target=0;
        for(int j=0;j<21;j++) {
            auto[a,b]=comp.edge[j];
            if((r>>(8*a+b)&1)||(r>>(8*b+a)&1))holes|=1ULL<<j;
            if(r>>(8*a+b)&1)target|=1ULL<<j;
        }
        std::vector<int> p{0,1,2,3,4,5,6};long long sum=0;
        do {
            auto plan=comp.plan(p,target,holes);sum+=plan.size();moves+=plan.size();checked++;
            auto state=p;
            for(auto[k,d]:plan) {
                if(k<0||k>=7||d<0||d>=7) {std::cerr<<"invalid operation class "<<c<<'\n';return 1;}
                u64 cover=0;bool visible=false;
                for(int x:state) {
                    if(x==k){visible=bool(comp.opq[x]&~cover);break;}
                    cover|=comp.opq[x];
                }
                if(!visible){std::cerr<<"invisible move class "<<c<<'\n';return 1;}
                state.erase(std::find(state.begin(),state.end(),k));state.insert(state.begin()+d,k);
            }
            u64 cover=0,display=0;
            for(int x:state){display|=comp.black[x]&~cover;cover|=comp.opq[x];}
            if((display^target)&holes) {std::cerr<<"wrong display class "<<c<<'\n';return 1;}
        }while(std::next_permutation(p.begin(),p.end()));
        if(sum!=kPoset7Classes[c].sum) {
            std::cerr<<"distance sum mismatch class "<<c<<": "<<sum<<" != "<<kPoset7Classes[c].sum<<'\n';return 1;
        }
        if(c%128==0)std::cerr<<"verified_classes = "<<(c-first+1)<<'\n';
    }
    std::cout<<"classes = "<<(last-first)<<"\nsource_states = "<<checked<<"\nlegal_moves = "<<moves
             <<"\nsum_mismatches = 0\nvisibility_errors = 0\ndisplay_errors = 0\n";
}
