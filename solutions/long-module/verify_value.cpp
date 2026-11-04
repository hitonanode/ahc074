#define main research_main
#include "model.cpp"
#undef main
int main(int argc,char**argv){if(argc<2)return 2;Model m(argv[1],8);std::mt19937_64 rng(6346294);
for(int test=0;test<1000;test++){
 State s(m.K);std::iota(s.begin(),s.end(),0);std::shuffle(s.begin(),s.end(),rng);if(test&1)s.erase(s.begin()+rng()%s.size());auto v=m.view(s);unsigned brute=1U<<v.display;
 for(int a=0;a<v.n;a++)for(int d=0;d<int(s.size());d++)brute|=1U<<m.view(Model::moved(s,v.visible[a],d)).display;
 auto [display,fast]=m.one_displays(s);assert(display==v.display);if(fast!=brute){std::cerr<<test<<' '<<fast<<' '<<brute<<'\n';return 3;}
}std::cout<<"1000 states including held-paper states: one-move display sets agree\n";return 0;}
