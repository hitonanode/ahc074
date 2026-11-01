#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

using U64 = std::uint64_t;
struct Paper { U64 opq=0, black=0; };
struct Option { int paper, depth, state; };

int main(int argc, char** argv) {
    if (argc != 3) { std::cerr << "Usage: representation_probe INPUT SAVED_OUTPUT\n"; return 1; }
    std::ifstream in(argv[1]), out(argv[2]);
    int n,k,p,r; in >> n >> k >> p >> r;
    if (!in || n!=64 || k!=192 || p!=256) return 2;
    std::vector<U64> targets(p);
    for (auto& a: targets) {
        std::string s; in>>s;
        for(int j=0;j<n;j++) if(s[j]=='1') a|=U64(1)<<j;
    }
    std::vector<Paper> papers(k);
    for(auto& a: papers) {
        std::string s; out>>s;
        if(!out || s.size()!=64) return 3;
        for(int j=0;j<n;j++) {
            if(s[j]!='.') a.opq|=U64(1)<<j;
            if(s[j]=='1') a.black|=U64(1)<<j;
        }
    }
    constexpr int m=6;
    U64 gm=0;
    for(int i=0;i<m;i++) gm |= papers[i].opq;
    std::unordered_map<U64, std::vector<int>> target_ids;
    for(int u=0;u<p;u++) target_ids[targets[u]&gm].push_back(u);
    std::array<int,m> perm; std::iota(perm.begin(),perm.end(),0);
    std::vector<std::vector<Option>> options(p);
    int state=0;
    do {
        U64 covered=0, shown=0;
        std::array<U64,m+1> prefix{};
        for(int i=0;i<m;i++) {
            int g=perm[i];
            shown |= papers[g].black & ~covered;
            covered |= papers[g].opq;
            prefix[i+1]=covered;
        }
        for(int x=m;x<k;x++) for(int t=0;t<=m;t++) {
            const auto& sheet = papers[x];
            const U64 generic = (shown & (prefix[t] | ~sheet.opq)) | (sheet.black & gm & ~prefix[t]);
            const auto found=target_ids.find(generic);
            if(found==target_ids.end()) continue;
            for(int u:found->second) {
                if((sheet.black ^ targets[u]) & sheet.opq & ~gm) continue;
                options[u].push_back({x,t,state});
            }
        }
        state++;
    } while(std::next_permutation(perm.begin(),perm.end()));
    long long totalpapers=0,totalstates=0,totaltop=0;
    int multi=0, indirect_only=0,maxpapers=0;
    std::cout << "target,top_papers,all_papers,states,alternate_ids\n";
    for(int u=0;u<p;u++) {
        std::set<int> top,all;
        for(auto option:options[u]) { all.insert(option.paper); if(option.depth==0) top.insert(option.paper); }
        totalpapers+=all.size(); totalstates+=options[u].size(); totaltop+=top.size();
        multi+=all.size()>1; indirect_only+=all.size()>top.size(); maxpapers=std::max(maxpapers,int(all.size()));
        std::cout << u << ',' << top.size() << ',' << all.size() << ',' << options[u].size() << ',';
        bool first=true;
        for(int x:all) if(!top.count(x)) { if(!first) std::cout << ';'; std::cout << x; first=false; }
        std::cout << '\n';
    }
    std::cerr << "generic_windows = " << __builtin_popcountll(gm)
              << "\nmean_top_papers = " << double(totaltop)/p
              << "\nmean_all_papers = " << double(totalpapers)/p
              << "\nmean_states = " << double(totalstates)/p
              << "\nmulti_paper_targets = " << multi
              << "\ninterleaving_extra_targets = " << indirect_only
              << "\nmax_papers = " << maxpapers << '\n';
}
