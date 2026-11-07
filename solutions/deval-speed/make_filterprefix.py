from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
needle='        auto evaluate = [&](const std::vector<Edit>& trial) {'
new='''        // A single exact four-edit prefix amortizes linked-list splices across
        // neighboring trials. The initial stack is immutable for this post pass.
        struct FilterPrefix {
            bool valid=false;u64 key=0;
            Links next,prev;
            std::array<u64,3> moved,breaks;
        } filter_prefix;
'''+needle
assert needle in s;s=s.replace(needle,new,1)
a=s.index(needle);b=s.index('            auto& path = path_buffer;',a);v=s[a:b]
v=v.replace('            auto next = initial_next, prev = initial_prev;','            Links next,prev;',1)
old='''                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;'''
new='''                u64 prefix_key=0;
                const bool can_cache=trial.size()>=4;
                if(can_cache)for(int i=0;i<4;++i)
                    prefix_key|=u64(trial[i].paper | ((trial[i].anchor+1)<<8))<<(16*i);
                int begin=0;
                if(can_cache&&filter_prefix.valid&&filter_prefix.key==prefix_key) {
                    next=filter_prefix.next;prev=filter_prefix.prev;
                    moved=filter_prefix.moved;breaks=filter_prefix.breaks;begin=4;
                } else { next=initial_next;prev=initial_prev; }
                for(int index=begin;index<int(trial.size());++index) {
                    const Edit& e=trial[index];
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;'''
assert old in v;v=v.replace(old,new,1)
old='''                    splice_after(next, prev, k, a);
                }'''
new='''                    splice_after(next, prev, k, a);
                    if(index==3) {
                        filter_prefix.valid=true;filter_prefix.key=prefix_key;
                        filter_prefix.next=next;filter_prefix.prev=prev;
                        filter_prefix.moved=moved;filter_prefix.breaks=breaks;
                    }
                }'''
assert old in v;v=v.replace(old,new,1)
s=s[:a]+v+s[b:]
d=ROOT/'solutions/deval-filterprefix';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-filterprefix

改良元: solutions/deval-vbranch-o3。

後処理の合法性判定の前処理で、直前に使った先頭4編集の後のリンク配列と変更箇所を保持する。次の試行の先頭4編集が完全一致すれば、その後からリンク操作を再開する。4個の紙番号とanchorは64ビットへ衝突なしに詰める。キャッシュは同一の初期スタックを使う1回の後処理内だけ有効。紙の列挙・浮動小数点・乱数・探索予算は変えない。
''')
print(len(s.encode()))
