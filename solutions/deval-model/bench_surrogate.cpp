// Contents: Benchmark entry (design-only, never an interactive solution).
#include "surrogate.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>

// ==== Benchmark entry ====
int main(int argc,char** argv) {
    if(argc<4){std::cerr<<"usage: bench_surrogate design.txt samples.bin repetitions\n";return 1;}
    std::ifstream design(argv[1]);
    auto s=deval::State::read(design);
    std::ifstream sf(argv[2],std::ios::binary|std::ios::ate);
    const std::size_t bytes=std::size_t(sf.tellg());
    std::vector<double> samples(bytes/sizeof(double));sf.seekg(0);sf.read(reinterpret_cast<char*>(samples.data()),bytes);
    const int ns=samples.size()/s.H,nrep=std::stoi(argv[3]);
    auto p=s.probabilities(2.);
    double checksum=0;
    using Clock=std::chrono::steady_clock;
    auto start=Clock::now();
    deval::CoverResult result;
    double utility=0;
    for(int it=0;it<nrep;++it) {
        auto donors=std::make_unique<deval::Donors>(s,p);
        utility=donors->head_utility(s,p);
        result=deval::expectation(s,*donors,p,samples.data(),ns,1.6);
        checksum+=result.mean()[1];
    }
    const double ms=std::chrono::duration<double,std::milli>(Clock::now()-start).count()/nrep;
    std::cout<<std::setprecision(15)<<"milliseconds "<<ms<<"\nheadutility "<<utility<<"\nmean";
    for(double v:result.mean())std::cout<<' '<<v;
    std::cout<<"\nchecksum "<<checksum<<'\n';
}
