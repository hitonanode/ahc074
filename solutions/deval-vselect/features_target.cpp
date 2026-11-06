#include "value_target.hpp"
#include <fstream>
#include <iostream>
int main(int argc,char** argv) {
    const int n=std::stoi(argv[1]);deval::GenericTable generic;
    std::string path;
    while(std::getline(std::cin,path)) {
        std::ifstream in(path);if(!in)return 1;
        auto state=deval::State::read(in);
        auto f=deval::static_features(state,generic);
        deval::add_stationary_features(f,state,n,2);
        std::array<double,deval::kTerms.size()> row{};
        for(int j=0;j<int(row.size());++j)row[j]=f.at(deval::kTerms[j].name);
        std::cout.write(reinterpret_cast<const char*>(row.data()),sizeof(row));
    }
}
