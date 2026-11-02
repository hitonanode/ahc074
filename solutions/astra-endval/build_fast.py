#!/usr/bin/env python3
"""計画内容を変えず、模擬の列検索をキャッシュする（研究専用）。"""
from pathlib import Path
import re
root=Path(__file__).resolve().parent
s=(root/'diagnostic.cpp').read_text()
cache='''
    // Cached views of the unchanged order. The membership key also checks the lifted paper
    // and every filler ID, because these records can change without moving a paper.
    mutable bool column_cache_valid=false;
    mutable int cache_top=-2;
    mutable std::vector<int> cache_fillers;
    mutable std::array<int,K> cache_positions{};
    mutable std::array<std::vector<int>,64> cache_columns;
    void ensure_columns() const {
        bool valid=column_cache_valid && cache_top==top_d && cache_fillers.size()==fillers.size();
        if(valid) for(int i=0;i<int(fillers.size());i++) if(cache_fillers[i]!=fillers[i].paper) {valid=false;break;}
        if(valid)return;
        cache_top=top_d;
        cache_fillers.clear();
        std::array<bool,K> extra{};
        if(top_d>=0)extra[top_d]=true;
        for(auto f:fillers)cache_fillers.push_back(f.paper),extra[f.paper]=true;
        for(int c=0;c<H;c++)cache_columns[c].clear();
        cache_positions.fill(-1);
        for(int i=0;i<int(order.size());i++) {
            int k=order[i];cache_positions[k]=i;
            if(col_of[k]>=0 && !extra[k])cache_columns[col_of[k]].push_back(k);
        }
        column_cache_valid=true;
    }
'''
s=s.replace('    int index_of(int k) const {\n        for (int i = 0; i < K; i++)\n            if (order[i] == k) return i;\n        return -1;\n    }',cache+'''    int index_of(int k) const {
        ensure_columns();
        return cache_positions[k];
    }''')
start=s.index('    void column_tops(');end=s.index('    // One dig',start)
s=s[:start]+'''    void column_tops(int l, int n, std::vector<int>& top) const {
        ensure_columns();
        const auto& v=cache_columns[l];
        top.assign(v.begin(),v.begin()+std::min<int>(std::max(1,n),v.size()));
    }
    int column_top(int l) const {
        ensure_columns();
        return cache_columns[l].empty()?-1:cache_columns[l][0];
    }
'''+s[end:]
s=s.replace('''        std::vector<int> v;
        for (int k : order)
            if (k != x && in_column(k, c)) v.push_back(k);''','''        ensure_columns();
        std::vector<int> v;
        for (int k : cache_columns[c]) if(k!=x)v.push_back(k);''')
start=s.index('    int handle_fix_cost(');end=s.index('    std::vector<int> fix_costs(',start)
s=s[:start]+'''    int handle_fix_cost(int l,int c) const {
        ensure_columns();
        int i=0;
        for(int k:cache_columns[l]) {
            if(int(paper[k].black>>handle[l]&1)==c)return i;
            i++;
        }
        return 0;
    }
'''+s[end:]
start=s.index('    int depth_in_column(');end=s.index('    //',start)
old=s[start:end]
assert 'return -1;' in old
s=s[:start]+'''    int depth_in_column(int x) const {
        ensure_columns();
        int pos=cache_positions[x];
        if(pos<0)return -1;
        int n=0;
        for(int k:cache_columns[col_of[x]]) {
            if(cache_positions[k]>=pos)break;
            n++;
        }
        return n;
    }
'''+s[end:]
# Maintain the cached per-column order after a relocation instead of rebuilding all columns
# after every dig. All other writes still invalidate the cache below.
start=s.index('    void move(int k, int d) {');end=s.index('    bool is_filler(',start)
s=s[:start]+'''    void cache_relocate(int k,int from,int to) {
        for(int i=std::min(from,to);i<=std::max(from,to);i++)cache_positions[order[i]]=i;
        const int c=col_of[k];
        if(c>=0 && in_column(k,c)) {
            auto& v=cache_columns[c];
            v.erase(std::find(v.begin(),v.end(),k));
            auto it=std::lower_bound(v.begin(),v.end(),to,[&](int x,int p){return cache_positions[x]<p;});
            v.insert(it,k);
        }
        column_cache_valid=true;
    }
    void move(int k,int d) {
        int i=index_of(k);
        if(i==d)return;
        if(check_vis && !visible(k))invalid=true;
        order.erase(order.begin()+i);
        order.insert(order.begin()+d,k);
        cache_relocate(k,i,d);
        ops.push_back({k,d});
    }
    void move_after(int k,int x) {
        const int kp=index_of(k),xp=index_of(x);
        move(k,xp+int(kp>xp));
    }
'''+s[end:]
old='''        int barrier = -1;
        for (int k : order)
            if (in_column(k, l) && int(paper[k].black >> handle[l] & 1) == color) {
                barrier = k;
                break;
            }'''
new='''        ensure_columns();
        int barrier = -1;
        for (int k : cache_columns[l])
            if (int(paper[k].black >> handle[l] & 1) == color) {
                barrier = k;
                break;
            }'''
assert old in s
s=s.replace(old,new)
# These are all writes to Solver::order inside its methods. Local replay vectors use 'ord'.
# Invalidation precedes the mutation; no change is made to the order or arithmetic.
begin=s.index('struct Solver {')
end=s.index('// Emergency design',begin)
body=s[begin:end]
body=re.sub(r'(?<![.\w])order\.(erase|insert)\(',r'column_cache_valid=false; order.\1(',body)
body=re.sub(r'(?<![.\w])order\s*=(?!=)\s*',r'column_cache_valid=false; order = ',body)
s=s[:begin]+body+s[end:]
# EXPAND=2 audits every added candidate without the 8-target screening.
s=s.replace('if(expansion_mode && int(endplans.size())>original_candidates+extra_keep)', 'if(expansion_mode==1 && int(endplans.size())>original_candidates+extra_keep)')
(root/'fast.cpp').write_text(s)
