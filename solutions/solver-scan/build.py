from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-lazy/main.cpp').read_text()
needle='    u64 handle_bits(u64 windows) const {'
a=s.index(needle);b=s.index('\n    // Orders the generic sheets',a)
old=s[a:b].replace('handle_bits(', 'handle_bits_old(')
new='''    static inline bool scan_fixes=true,packed_bits=true;
    bool handle_cache_ready=false;
    int handle_first_byte=0,handle_last_byte=7;
    std::array<std::array<u64,256>,8> handle_lookup{};
    void init_handle_cache(){
        handle_lookup={};handle_first_byte=7;handle_last_byte=0;
        for(int c=0;c<H;c++){
            int j=handle[c];handle_first_byte=std::min(handle_first_byte,j/8);handle_last_byte=std::max(handle_last_byte,j/8);
            for(int v=0;v<256;v++)if(v>>(j%8)&1)handle_lookup[j/8][v]|=1ULL<<c;
        }
        handle_cache_ready=true;
    }
    u64 handle_bits(u64 windows)const{
        if(!packed_bits||!handle_cache_ready)return handle_bits_old(windows);
        u64 r=0;for(int j=handle_first_byte;j<=handle_last_byte;j++)r|=handle_lookup[j][(windows>>(8*j))&255];return r;
    }
'''
s=s[:a]+new+old+s[b:]
needle='    std::vector<int> fix_costs(int u, u64 hh) const {'
a=s.index(needle);b=s.index('    // The level just past',a)
old=s[a:b].replace('fix_costs(', 'fix_costs_old(')
new='''    std::vector<int> fix_costs(int u,u64 hh)const{
        if(!scan_fixes)return fix_costs_old(u,hh);
        std::vector<int> fix(H,0);
        u64 pending=hh;
        for(int k:order){
            int c=col_of[k];
            if(c<0||!(pending>>handle[c]&1)||k==top_d||is_filler(k))continue;
            if(!((paper[k].black^A[u])>>handle[c]&1))pending&=~(1ULL<<handle[c]);
            else fix[c]++;
        }
        for(int c=0;c<H;c++)if(pending>>handle[c]&1)fix[c]=0;
        return fix;
    }
'''
s=s[:a]+new+old+s[b:]
s=s.replace('    int level_past(u64 wrong) const {','    int level_past(u64 wrong) const {\n        if(packed_bits&&handle_cache_ready){u64 mask=handle_bits(wrong);return mask?64-__builtin_clzll(mask):0;}')
s=s.replace('    solver.h_opq.resize(K);','    solver.init_handle_cache();\n    solver.h_opq.resize(K);')
(p/'main.cpp').write_text(s)
