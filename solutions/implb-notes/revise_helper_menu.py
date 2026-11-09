from pathlib import Path
p=Path('solutions/d30b-req-stack/main.cpp');s=p.read_text()
a='    void refill_or_return(int u, FillerList olds, u64& pre_cov, FillerList& placed, int helper_a=-1, int helper_b=-1) {'
b='    template<bool WithHelpers=false>\n'+a
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace('            if(x==helper_a || x==helper_b){return_paper(x,u,1);continue;}','            if constexpr(WithHelpers) if(x==helper_a || x==helper_b){return_paper(x,u,1);continue;}')
for old in ['refill_or_return(u,vis_old,pre_cov,placed,x,y);','refill_or_return(u,def_old,pre_cov,placed,x,y);','refill_or_return(u,olds,pre_cov,placed,x,y);']:
 assert s.count(old)==1;s=s.replace(old,old.replace('refill_or_return(', 'refill_or_return<true>('))
a='''    static bool helper_menu_enabled() {
#ifdef LOCAL_BENCH
        if(const char* p=std::getenv("D30B_HELPER_MENU"))return std::atoi(p)!=0;
#endif
        return true;
    }'''
b='''    long long helper_menu_no_reuse=0;
    static int helper_menu_mode() {
#ifdef LOCAL_BENCH
        static const int mode=[] {
            const char* p=std::getenv("D30B_HELPER_MENU");
            return p?std::clamp(std::atoi(p),0,2):2;
        }();
        return mode;
#else
        return 2;
#endif
    }'''
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace('if(helper_menu_enabled() && (st0.top_d>=0 || !st0.fillers.empty())) {','if(helper_menu_mode() && (st0.top_d>=0 || !st0.fillers.empty())) {')
a='''        if(lvl>=0) {
            FillerList vis_old,def_old;'''
b='''        // Keeping/repositioning fillers alone was too costly for its measured
        // score gain. Spend the extra plan only on the new previous-product reuse.
        if(lvl<0 && helper_menu_mode()==2){++helper_menu_no_reuse;return false;}
        if(lvl>=0) {
            FillerList vis_old,def_old;'''
assert s.count(a)==1;s=s.replace(a,b)
a='              << "\\nhelper_menu_reuse = " << solver.helper_menu_reuse'
b='              << "\\nhelper_menu_no_reuse = " << solver.helper_menu_no_reuse\n'+a
assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
