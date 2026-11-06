#include "../deval-model/value.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
int main() {
    deval::DesignValue value;
    std::string path;
    std::cout << std::setprecision(17);
    while(std::getline(std::cin,path)) {
        std::ifstream in(path);
        if(!in) return 1;
        auto state=deval::State::read(in);
        std::cout << value(state) << '\n';
    }
}
