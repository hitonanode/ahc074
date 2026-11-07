"""Generate/run small data-structure tests; no solver or request planner is executed."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
small=(ROOT/'solutions/deval-smallfill/main.cpp').read_text()
a=small.index('    struct Filler {');b=small.index('    FillerList fillers;',a)
container=small[a:b]
orig=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
new=(ROOT/'solutions/deval-hungarian-vec/main.cpp').read_text()
def hung(s):
    a=s.index('std::vector<int> hungarian(');b=s.index('// The filler value of the column heads',a)
    return s[a:b].replace('AF_SCOPE(hungarian, 1);','')
code='''#include <algorithm>
#include <array>
#include <vector>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <cassert>
#include <iostream>
#include <immintrin.h>
struct Test {
'''+container+'''};
'''+hung(orig).replace('hungarian(','original(')+'''\n__attribute__((target("avx2"))) '''+hung(new)+'''
int main(){
    uint64_t rng=37484691;
    auto next=[&](){rng^=rng<<13;rng^=rng>>7;return rng^=rng<<17;};
    Test::FillerList a,b;std::vector<Test::Filler> x,y;
    auto eq=[](const auto& a,const auto& b){assert(a.size()==b.size());for(size_t i=0;i<a.size();++i)assert(a[i].paper==b[i].paper&&a[i].lvl==b[i].lvl&&a[i].hi==b[i].hi);};
    for(int it=0;it<100000;++it){
        const int op=next()%6;
        if(op==0&&x.size()<192){Test::Filler f{int(next()%192),int(next()%35),int(next()%35)};a.push_back(f);x.push_back(f);}
        if(op==1){const int m=next()%7;auto pred=[&](auto f){return f.paper%7==m;};a.erase_if(pred);std::erase_if(x,pred);}
        if(op==2){b=a;y=x;}
        if(op==3){a=b;x=y;}
        if(op==4){Test::FillerList c(a);a=std::move(c);}
        if(op==5){std::sort(a.begin(),a.end(),[](auto f,auto g){return f.paper<g.paper;});std::sort(x.begin(),x.end(),[](auto f,auto g){return f.paper<g.paper;});}
        eq(a,x);eq(b,y);
    }
    for(int it=0;it<500;++it){const int n=1+next()%50;std::vector cost(n,std::vector<double>(n));
        for(auto& row:cost)for(auto& v:row)v=int(next()%17)*.1;
        assert(original(cost)==hungarian(cost));
    }
    std::cout<<"filler operations=100000, tied Hungarian matrices=500: PASS\\n";
}
'''
path=HERE/'backend_unit.cpp';path.write_text(code)
for compiler in ['g++','clang++']:
    binary=HERE/('backend_unit_'+compiler.replace('+','p'))
    subprocess.run([compiler,'-std=c++23','-O2',str(path),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
