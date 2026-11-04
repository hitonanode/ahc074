#define main eight_solver_main
#include "main.cpp"
#undef main
#define main table_generator_main
#include "generate.cpp"
#undef main

int main(){
    Graph graph(8);
    std::mt19937_64 random(812307);
    Comparator comp;
    comp.init(8,28,random);
    auto& table=Poset8Costs::get();
    for(int sample=0;sample<128;++sample){
        u64 closed=table.relations[random()%table.relations.size()];
        int expected=graph.sum(closed)+graph.sum(transpose8(closed));
        assert(table.cost(closed)==expected+1);
        // Relabeling must preserve the exact cost and the table class.
        std::array<int,8> permutation{0,1,2,3,4,5,6,7};
        std::shuffle(permutation.begin(),permutation.end(),random);
        u64 permuted=0;
        for(u64 bits=closed;bits;bits&=bits-1){
            int bit=__builtin_ctzll(bits);
            permuted|=1ULL<<(8*permutation[bit/8]+permutation[bit%8]);
        }
        assert(table.cost(permuted)==expected+1);
    }
    int checked_moves=0;
    for(int sample=0;sample<2000;++sample){
        std::vector<int> initial(8),target_order(8);
        std::iota(initial.begin(),initial.end(),0);target_order=initial;
        std::shuffle(initial.begin(),initial.end(),random);
        std::shuffle(target_order.begin(),target_order.end(),random);
        u64 color=0,covered=0;
        for(int paper:target_order){color|=comp.black[paper]&~covered;covered|=comp.opq[paper];}
        u64 holes=random()&low_bits(28);
        auto moves=comp.plan(initial,color,holes);
        auto order=initial;
        for(auto[paper,depth]:moves){
            assert(paper>=0&&paper<8&&depth>=0&&depth<8);
            u64 seen=0;bool visible=false;
            for(int x:order){if(x==paper){visible=bool(comp.opq[x]&~seen);break;}seen|=comp.opq[x];}
            assert(visible);
            order.erase(std::find(order.begin(),order.end(),paper));order.insert(order.begin()+depth,paper);
            ++checked_moves;
        }
        u64 shown=0;covered=0;
        for(int paper:order){shown|=comp.black[paper]&~covered;covered|=comp.opq[paper];}
        assert(!((shown^color)&holes));
    }
    std::cout<<"Exact cost cases = 128\nRelabelings = 128\nLegal plans = 2000\nLegal moves = "<<checked_moves<<'\n';
}
