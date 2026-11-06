// Independent offline replay checker for AHC074.
// Rules mirror the supplied tools/src/lib.rs State::apply / score.
// Usage: replay-checker ORIGINAL_INPUT OUTPUT [K_OVERRIDE]
// This is not the official Rust tester; it supports the counterfactual K budget.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
using U64 = std::uint64_t;
struct Paper { U64 opaque=0, black=0; };
std::string esc(const std::string& s) {
    std::string r;
    for(char c:s) { if(c=='"'||c=='\\') r+='\\'; if(c=='\n') r+="\\n"; else r+=c; }
    return r;
}
int main(int argc, char** argv) {
    long long moves=0, errors=0;
    int round=-1, step=-1;
    try {
        if(argc!=3 && argc!=4) throw std::runtime_error("Usage: replay-checker INPUT OUTPUT [K]");
        std::ifstream in(argv[1]), out(argv[2]);
        if(!in || !out) throw std::runtime_error("Cannot open input or output");
        int N,K,P,R;
        if(!(in>>N>>K>>P>>R)) throw std::runtime_error("Invalid input header");
        if(argc==4) K=std::stoi(argv[3]);
        if(N<1 || N>64 || K<1 || P<1 || R<1) throw std::runtime_error("Invalid dimensions");
        std::vector<U64> target(P);
        std::vector<int> req(R);
        for(auto& a:target) {
            std::string s; if(!(in>>s) || int(s.size())!=N) throw std::runtime_error("Invalid target");
            for(int j=0;j<N;j++) { if(s[j]!='0'&&s[j]!='1') throw std::runtime_error("Invalid target color"); if(s[j]=='1') a|=U64(1)<<j; }
        }
        for(int& u:req) if(!(in>>u) || u<0 || u>=P) throw std::runtime_error("Invalid request");
        std::vector<Paper> papers(K);
        std::vector<int> order(K); std::iota(order.begin(),order.end(),0);
        for(auto& p:papers) {
            std::string s; if(!(out>>s) || int(s.size())!=N) throw std::runtime_error("Invalid paper pattern length");
            for(int j=0;j<N;j++) {
                if(s[j]!='0'&&s[j]!='1'&&s[j]!='.') throw std::runtime_error("Invalid paper color");
                if(s[j]!='.') p.opaque|=U64(1)<<j;
                if(s[j]=='1') p.black|=U64(1)<<j;
            }
        }
        std::vector<int> counts; int max_moves=0;
        for(round=0;round<R;round++) {
            int m; if(!(out>>m) || m<0 || m>2*K) throw std::runtime_error("Invalid move count");
            counts.push_back(m); max_moves=std::max(max_moves,m);
            for(step=0;step<m;step++) {
                int k,d; if(!(out>>k>>d) || k<0 || k>=K || d<0 || d>=K) throw std::runtime_error("Invalid move indices");
                U64 exposed=papers[k].opaque;
                int pos=0;
                while(pos<K && order[pos]!=k) { exposed &= ~papers[order[pos]].opaque; ++pos; }
                if(pos==K) throw std::runtime_error("Corrupt stack");
                if(!exposed) throw std::runtime_error("Moved an invisible paper: "+std::to_string(k));
                if(pos<d) std::rotate(order.begin()+pos,order.begin()+pos+1,order.begin()+d+1);
                else if(pos>d) std::rotate(order.begin()+d,order.begin()+pos,order.begin()+pos+1);
                ++moves;
            }
            U64 covered=0,black=0;
            for(int k:order) { black|=papers[k].black & ~covered; covered|=papers[k].opaque; }
            errors += black != target[req[round]];
        }
        std::string extra; if(out>>extra) throw std::runtime_error("Extra output after last request");
        std::cout<<"{\"valid\":true,\"K\":"<<K<<",\"requests\":"<<R<<",\"moves\":"<<moves<<",\"errors\":"<<errors
                 <<",\"score\":"<<(moves+2LL*K*errors)<<",\"max_request_moves\":"<<max_moves<<",\"per_request\":[";
        for(int i=0;i<R;i++) std::cout<<(i?",":"")<<counts[i];
        std::cout<<"]}\n";
        return 0;
    } catch(const std::exception& e) {
        std::cout<<"{\"valid\":false,\"error\":\""<<esc(e.what())<<"\",\"round\":"<<round<<",\"step\":"<<step
                 <<",\"moves\":"<<moves<<",\"errors\":"<<errors<<"}\n";
        return 2;
    }
}
