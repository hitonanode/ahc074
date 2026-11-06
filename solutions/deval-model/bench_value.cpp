// Contents: Final V verification and timing; no request planner is linked.
#include "value.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>

// ==== Final V verification and timing ====
int main(int argc,char** argv) {
    if(argc<3)return 1;
    using Clock=std::chrono::steady_clock;
    auto start=Clock::now();deval::DesignValue value;
    const double init=std::chrono::duration<double,std::milli>(Clock::now()-start).count();
    std::ifstream in(argv[1]);const auto state=deval::State::read(in);
    const int n=std::stoi(argv[2]);double sum=0,last=0;
    start=Clock::now();
    for(int i=0;i<n;++i){last=value(state);sum+=last;}
    const double ms=std::chrono::duration<double,std::milli>(Clock::now()-start).count()/n;
    std::cout<<std::setprecision(17)<<last<<' '<<ms<<' '<<init<<' '<<sum<<'\n';
}
