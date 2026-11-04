from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/sparse-map/main.cpp').read_text()
old='''        if (!complete || int(current.size()) != M) return {{-1, -1}};'''
assert old in s
s=s.replace(old,'''        if (int(current.size()) != M) return {{-1, -1}};
        if(!complete){
            // Sparse comparison graphs can hide several generic papers.
            // Use the actual legal-move graph rather than the complete-graph
            // subsequence construction in this case.
            assert(!perms.empty());
            const int start=order_index(current);int best=-1,value=255;
            for(int t:satisfying(target,holes))if(distance(start,t)<value)value=distance(start,t),best=t;
            return best>=0?path(start,best):std::vector<std::pair<int,int>>{{-1,-1}};
        }''',1)
(p/'main.cpp').write_text(s)
