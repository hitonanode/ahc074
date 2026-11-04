from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'perforated-eight/main.cpp').read_text()
a=s.index('    double adaptive_next_cost() const {')
b=s.index('    // Puts paper x',a)
old=s[a:b]
new=old.replace('adaptive_next_cost()', 'adaptive_next_cost_array()')
new=new.replace('std::vector<int> rank(H, 0);', 'std::array<int,64> rank{};')
new=new.replace('std::vector<std::array<int, 2>> first(H);', 'std::array<std::array<int,2>,64> first;')
new=new.replace('std::vector<std::array<bool, 2>> available(H, {false, false});', 'std::array<std::array<bool,2>,64> available{};\n        std::array<bool,K> extra{};if(top_d>=0)extra[top_d]=true;for(auto f:fillers)extra[f.paper]=true;')
new=new.replace('k == top_d || is_filler(k)', 'extra[k]')
wrapper='    static inline bool array_cost=true,array_insert=true;\n    double adaptive_next_cost()const{return array_cost?adaptive_next_cost_array():adaptive_next_cost_old();}\n'
s=s[:a]+wrapper+old.replace('adaptive_next_cost()', 'adaptive_next_cost_old()')+new+s[b:]
a=s.index('    void adaptive_insert(int x, int u, int barrier = -1, int mode = 2) {')
b=s.index('    // ------------------------------------------------------------------------------------------',a)
old=s[a:b]
new=old.replace('adaptive_insert(', 'adaptive_insert_array(')
new=new.replace('std::vector<int> v;', 'std::array<int,K> v;int n=0;')
new=new.replace('v.push_back(k)', 'v[n++]=k')
new=new.replace('        const int n = v.size();\n','')
new=new.replace('v.end()', 'v.begin()+n')
new=new.replace('std::vector<double> suffix(n + 1, 0.0);', 'std::array<double,K+1> suffix; suffix[n]=0;')
new=new.replace('v.back()', 'v[n-1]')
wrapper='    void adaptive_insert(int x,int u,int barrier=-1,int mode=2){if(array_insert)adaptive_insert_array(x,u,barrier,mode);else adaptive_insert_old(x,u,barrier,mode);}\n'
s=s[:a]+wrapper+old.replace('adaptive_insert(', 'adaptive_insert_old(')+new+s[b:]
(p/'main.cpp').write_text(s)
