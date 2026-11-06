// Contents: Complete design evaluator benchmark (no request planner).
#include "design_features.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>

// ==== Complete design evaluator benchmark ====
int main(int argc,char** argv) {
    if(argc<4){std::cerr<<"usage: bench_features design.txt mode repetitions\n";return 1;}
    using Clock=std::chrono::steady_clock;
    auto start=Clock::now();deval::GenericTable table;
    const double init_ms=std::chrono::duration<double,std::milli>(Clock::now()-start).count();
    std::ifstream input(argv[1]);auto s=deval::State::read(input);
    const std::string mode=argv[2];int repeats=std::stoi(argv[3]);
    start=Clock::now();deval::FeatureMap f;double checksum=0;
    for(int rep=0;rep<repeats;++rep) {
        s.prepare();f=deval::static_features(s,table);
        if(mode=="compact")deval::add_filler_features(f,s,4.,{1.,2.2},32);
        else if(mode=="fast")deval::add_filler_features(f,s,2.,{1.6},32);
        else if(mode=="stationary")deval::add_stationary_features(f,s,16,4);
        else if(mode=="stationary32")deval::add_stationary_features(f,s,32,2);
        else if(mode=="filler")for(double strength:{0.,1.,2.,4.})deval::add_filler_features(f,s,strength,{1.,1.6,2.2},128);
        else if(mode!="static")throw std::runtime_error("mode");
        checksum+=f.at("col");
    }
    const double ms=std::chrono::duration<double,std::milli>(Clock::now()-start).count()/repeats;
    std::cout<<std::setprecision(17)<<"__milliseconds "<<ms<<"\n__init_milliseconds "<<init_ms<<"\n__checksum "<<checksum<<'\n';
    for(const auto& [name,value]:f)std::cout<<name<<' '<<value<<'\n';
}
