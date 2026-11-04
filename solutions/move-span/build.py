from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
a=s.index('    int index_of(int k) const {',s.index('struct Solver'))
b=s.index('    bool visible(int k) const {',a)
s=s[:a]+'''    static inline int move_mode=0;
    mutable bool position_dirty=true;
    mutable std::array<int,K> position_cache;
    int index_of(int k) const {
        if(move_mode==2){
            if(position_dirty){for(int i=0;i<K;i++)position_cache[order[i]]=i;position_dirty=false;}
            return position_cache[k];
        }
        for(int i=0;i<K;i++)if(order[i]==k)return i;
        return -1;
    }
    // Removing and reinserting only rotates the segment between the two ranks.
    void shift_order(int k,int from,int to){
        if(move_mode==2){
            if(from<to)for(int i=from;i<to;i++){order[i]=order[i+1];position_cache[order[i]]=i;}
            else for(int i=from;i>to;i--){order[i]=order[i-1];position_cache[order[i]]=i;}
            order[to]=k;position_cache[k]=to;
        }else{
            if(from<to)std::move(order.begin()+from+1,order.begin()+to+1,order.begin()+from);
            else std::move_backward(order.begin()+to,order.begin()+from,order.begin()+from+1);
            order[to]=k;position_dirty=true;
        }
    }
'''+s[b:]
old='''        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);'''
new='''        if(move_mode)shift_order(k,i,d);
        else{order.erase(order.begin()+i);order.insert(order.begin()+d,k);position_dirty=true;}'''
assert s.count(old)==1;s=s.replace(old,new)
old='''        order.erase(order.begin() + i);
        int j = 0;
        while (order[j] != x) j++;
        order.insert(order.begin() + j + 1, k);
        ops.push_back({k, j + 1});'''
new='''        if(move_mode){
            int dest=index_of(x)+1;if(i<dest)dest--;
            shift_order(k,i,dest);ops.push_back({k,dest});
        }else{
            order.erase(order.begin()+i);int j=0;while(order[j]!=x)j++;
            order.insert(order.begin()+j+1,k);position_dirty=true;ops.push_back({k,j+1});
        }'''
assert s.count(old)==1;s=s.replace(old,new)
for needle in ['order = e.out_order;','order = st.order;','order = std::move(ord);']:
 assert s.count(needle)==1,(needle,s.count(needle));s=s.replace(needle,needle+'position_dirty=true;')
(p/'main.cpp').write_text(s)
