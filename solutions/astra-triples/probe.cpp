#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using U = std::uint64_t;
struct Comparator {
    std::array<std::array<U,6>,6> direction{};
    U mask = 0;
    bool sat(U target, U holes) const {
        std::array<unsigned,6> reach{};
        holes &= mask;
        for(int a=0;a<6;++a) for(int b=a+1;b<6;++b) {
            U ab=direction[a][b], ba=direction[b][a];
            if (holes & ((target&ab)|(~target&ba))) reach[a] |= 1u<<b;
            if (holes & ((target&ba)|(~target&ab))) reach[b] |= 1u<<a;
            if((reach[a]>>b&1u)&&(reach[b]>>a&1u)) return false;
        }
        for(int k=0;k<6;++k) for(int a=0;a<6;++a) if(reach[a]>>k&1u) reach[a] |= reach[k];
        for(int a=0;a<6;++a) if(reach[a]>>a&1u) return false;
        return true;
    }
};
int main(int argc,char**argv){
    if(argc!=3) return 2;
    std::ifstream fi(argv[1]),fo(argv[2]);
    int n,k,p,r;
    if(!(fi>>n>>k>>p>>r) || n!=64 || k!=192 || p!=256 || r<1 || !fo) return 2;
    std::vector<U>A(p); std::string s;
    for(auto&a:A){
        if(!(fi>>s) || s.size()!=64 || s.find_first_not_of("01")!=std::string::npos) return 2;
        for(int j=0;j<n;++j)if(s[j]=='1')a|=U(1)<<j;
    }
    std::array<std::string,6>paper;
    for(auto&x:paper) if(!(fo>>x) || x.size()!=64 || x.find_first_not_of("01.")!=std::string::npos) return 2;
    Comparator co;
    for(int j=0;j<n;++j){
        int white=-1,black=-1,cnt=0;
        for(int x=0;x<6;++x){ if(paper[x][j]=='1')black=x,++cnt; if(paper[x][j]=='0')white=x,++cnt; }
        if(cnt==0)continue;
        if(cnt!=2 || white<0 || black<0) return 3;
        co.mask|=U(1)<<j; co.direction[black][white]|=U(1)<<j;
    }
    std::vector<std::vector<bool>>ok(p,std::vector<bool>(p));
    long long edges=0,near=0,triangles=0,valid=0,anchor=0;
    double minholes=64,sumholes=0; std::array<int,256>participates{};
    for(int u=0;u<p;++u)for(int v=u+1;v<p;++v)if(co.sat(A[u],A[u]^A[v])){
        ok[u][v]=ok[v][u]=true;++edges;near+=std::popcount(A[u]^A[v])<=26;
    }
    for(int u=0;u<p;++u)for(int v=u+1;v<p;++v)if(ok[u][v])for(int w=v+1;w<p;++w)if(ok[u][w]&&ok[v][w]){
        ++triangles; const U holes=(A[u]^A[v])|(A[u]^A[w]);
        if(!co.sat(A[u],holes)||!co.sat(A[v],holes)||!co.sat(A[w],holes))continue;
        ++valid;if(!(~holes&~co.mask))continue;++anchor;
        const int h=std::popcount(holes);sumholes+=h;minholes=std::min(minholes,double(h));
        participates[u]=participates[v]=participates[w]=1;
    }
    int covered=0;for(int x:participates)covered+=x;
    std::cout<<edges<<','<<near<<','<<triangles<<','<<valid<<','<<anchor<<','<<covered<<','<<(anchor?sumholes/anchor:0)<<','<<(anchor?minholes:0)<<'\n';
}
