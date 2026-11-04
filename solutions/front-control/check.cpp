#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#include "module.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <tuple>
int main(int argc,char**argv){
 if(argc<2)return 2;std::ifstream input(argv[1]);int k=0,p=0,n=0;input>>k>>p>>n;if(!input||n!=2||k>7)return 3;
 std::vector<int>op(k),ink(k);for(int i=0;i<k;i++){int id,col,color,allowed;input>>id>>col>>op[i]>>color>>allowed;ink[i]=color&op[i];}
 std::map<std::tuple<int,int,int>,int>counts;
 for(int u=0;u<p;u++){int paper,mask,color;input>>paper>>mask>>color;if(paper>=0||mask)counts[{paper,mask,color}]++;}
 std::vector<FrontModel::Event>events;for(auto[key,c]:counts){auto[paper,mask,color]=key;events.push_back({paper,mask,color,c});}
 FrontModel model(op,ink,events);model.solve(1000,2e-7);
 std::cout<<std::setprecision(12)<<"{\"papers\":"<<k<<",\"lower\":"<<model.lower<<",\"upper\":"<<model.upper<<",\"iterations\":"<<model.iterations<<",\"seconds\":"<<model.seconds<<"}\n";
}
