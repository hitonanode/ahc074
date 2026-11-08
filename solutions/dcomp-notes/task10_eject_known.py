from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-eject-screen/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(a[:90],s.count(a));s=s.replace(a,b)
sub('        bool active = false;','        bool active = false, display_proven=false;')
sub('auto prepare_screen = [&](int i, int j, const std::vector<Edit>* source=nullptr)', 'auto prepare_screen = [&](int i, int j, const std::vector<Edit>* source=nullptr, const Links* known_next=nullptr, const Links* known_prev=nullptr)')
sub('''            S.active = false;
            S.replay_ready = false;''','''            S.active = false; S.display_proven=known_next!=nullptr;
            S.replay_ready = false;''')
a=s.index('        auto prepare_screen =');b=s.index('        // true: the trial',a)
t=s[a:b]
old='''            auto nx = initial_next, pv = initial_prev;
            for (int t = 0; t < n; t++) {'''
new='''            // Eject already constructed this exact G and proved the insertion
            // interval repairs its display. Reuse both, under the same commutation test.
            if(known_next){S.next=*known_next;S.prev=*known_prev;S.active=true;return;}
            auto nx = initial_next, pv = initial_prev;
            for (int t = 0; t < n; t++) {'''
assert t.count(old)==1;t=t.replace(old,new);s=s[:a]+t+s[b:]
sub('''            const u64 shown = (S.disp & ~vis) | (paper[S.k].black & vis);''','''            const u64 shown = S.display_proven?A[u]:(S.disp & ~vis) | (paper[S.k].black & vis);''')
# Avoid reading old coverage data for the proven path.
sub('''            const u64 above = a < 0 ? 0 : S.visited[a] == S.epoch ? S.cover_through[a] : ~u64(0);''','''            const u64 above = S.display_proven?0:a < 0 ? 0 : S.visited[a] == S.epoch ? S.cover_through[a] : ~u64(0);''')
a=s.index('void eject_repairs(');b=s.index('// ==== Post-processing: two deletions and two repairs',a)
t=s[a:b]
old='''                auto nx = initial_next;
                {
                    auto pv = initial_prev;'''
assert t.count(old)==1;t=t.replace(old,'''                auto nx = initial_next;
                auto pv = initial_prev;
                {''')
old='prepare_screen(t,-1,&next);';assert t.count(old)==1;t=t.replace(old,'prepare_screen(t,-1,&next,&nx,&pv);');s=s[:a]+t+s[b:]
for check in [False,True]:
 p=r/'solutions'/('dcomp-eject-known'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define SCREEN_REPLAY_CHECK\n#define SCREEN_LINK_CHECK\n#define SCREEN_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-eject-screen\n\n取り出し修復が既に構成したGの双方向リンクを共有する。修復anchorの区間はGから紙を除いた表示を必ず直す区間なので、可換条件を満たした場合の表示再計算も省く。元の完全再生を使う検証版で最終リンク・表示・合法性・操作列を照合する。予算・列挙順・評価式とログは維持、時間fallbackなし。\n')
