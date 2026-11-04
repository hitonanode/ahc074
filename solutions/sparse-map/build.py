from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-eight/main.cpp').read_text()
s=s.replace('struct WindowStats {','''static int sparse_map_mode=0;
bool sparse_allowed(int a,int b){
    if(a>b)std::swap(a,b);
    if(sparse_map_mode==2)return !(a==0&&b==1);
    if(sparse_map_mode==3)return !(a%2==0&&b==a+1);
    return true;
}
struct WindowStats {''')
s=s.replace('for (int c : counts)\n        if (!c) return stats;', 'for (int c : counts)\n        if (!c && !sparse_map_mode) return stats;')
s=s.replace('counts[ea] >= 2', 'counts[ea] >= (sparse_map_mode?1:2)')
s=s.replace('if (counts[ea] < 2) return false;', 'if (counts[ea] < (sparse_map_mode?1:2)) return false;')
needle='''        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};'''
assert needle in s
s=s.replace(needle,'''        if(sparse_map_mode){
            bool allowed=sparse_allowed(ep[eb].first,ep[eb].second);
            if(!mask[ea]){
                // An isolated paper could never be moved. Keep every
                // generic paper incident to at least one printed comparison.
                unsigned covered=0;
                for(int e=0;e<ne;e++)if(mask[e])covered|=(1U<<ep[e].first)|(1U<<ep[e].second);
                allowed&=covered==((1U<<m)-1);
            }
            if(!allowed){mask[ea]=olda;mask[eb]=oldb;pol=oldpol;return false;}
        }
'''+needle)
# Build genuine legal transitions even for a graph missing comparison edges.
s=s.replace('''        for (int a = 0; a < n; a++)
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d) {''','''        for (int a = 0; a < n; a++)
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d) {
                        u64 blocked=0;for(int j=0;j<pos;j++)blocked|=opq[perms[a][j]];
                        if(!(opq[perms[a][pos]]&~blocked))continue;''',1)
(p/'main.cpp').write_text(s)
