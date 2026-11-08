from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(a[:100],s.count(a));s=s.replace(a,b)
sub('        bool replay_ready=false, replay_ok=false, k_visible=false;','        bool replay_ready=false, replay_ok=false, k_visible=false;\n        const std::vector<Edit>* edit_source=nullptr;')
a=s.index('        auto prepare_screen_replay =');b=s.index('        // Only a successful,',a)
t=s[a:b];t=t.replace('            auto& S=anchor_screen;','            auto& S=anchor_screen;\n            const auto& screen_edits=*S.edit_source;');t=t.replace('edits[','screen_edits[').replace('edits.size()','screen_edits.size()');s=s[:a]+t+s[b:]
sub('OP_TAG(path_tags.push_back(edits[S.i].tag);)','OP_TAG(path_tags.push_back((*S.edit_source)[S.i].tag);)')
a=s.index('        auto prepare_screen =');b=s.index('        // true: the trial',a)
t=s[a:b];t=t.replace('auto prepare_screen = [&](int i, int j)', 'auto prepare_screen = [&](int i, int j, const std::vector<Edit>* source=nullptr)');t=t.replace('            auto& S = screen;', '            auto& S = screen;\n            S.edit_source=source?source:&edits;\n            const auto& screen_edits=*S.edit_source;');t=t.replace('edits[','screen_edits[').replace('edits.size()','screen_edits.size()');s=s[:a]+t+s[b:]
# Avoid old optional display checker using the ordinary outer edits for eject groups.
a=s.index('        auto screen_rejects =');b=s.index('        auto delete_singles',a)
t=s[a:b];t=t.replace('for (int t = 0; t < int(edits.size()); t++)','for (int t = 0; t < int(S.edit_source->size()); t++)').replace('edits[t].paper','(*S.edit_source)[t].paper').replace('edits[t].anchor','(*S.edit_source)[t].anchor');s=s[:a]+t+s[b:]
s=s.replace('initial_bytes, evaluate);\n            if (neutral_collect)', 'initial_bytes, evaluate, prepare_screen, screen_rejects);\n            if (neutral_collect)')
s=s.replace('initial_bytes, evaluate, 1);','initial_bytes, evaluate, prepare_screen, screen_rejects, 1);')
sub('''    template <class Evaluate>
    __attribute__((target("avx2"))) void eject_repairs''','''    template <class Evaluate,class Prepare,class Screen>
    __attribute__((target("avx2"))) void eject_repairs''')
sub('''const Links& initial_prev, const ByteOrder& initial_bytes, Evaluate& evaluate, int removed = 2)''','''const Links& initial_prev, const ByteOrder& initial_bytes, Evaluate& evaluate, Prepare& prepare_screen, Screen& screen_rejects, int removed = 2)''')
sub('''                        for (int ai = 0; ai < count; ai++) {
                            next.assign''','''                        bool prepared_screen=false;
                        for (int ai = 0; ai < count; ai++) {
                            next.assign''')
sub('''                            eject_trials++;
                            if (evaluate(next))''','''                            eject_trials++;
                            if(!prepared_screen){prepare_screen(t,-1,&next);prepared_screen=true;}
                            if(screen_rejects(anchors[ai]))continue;
                            if (evaluate(next))''')
for check in [False,True]:
 p=r/'solutions'/('dcomp-eject-screen'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define SCREEN_REPLAY_CHECK\n#define SCREEN_LINK_CHECK\n#define SCREEN_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n取り出し修復でも、挿入する同じ紙・同じ時刻のanchor群に対し、可換な付け替えの最終リンクと合法性再生を共有する。挿入後に紙やanchorが動く場合は元の完全評価を使う。元の修復候補・列挙順序・予算は維持。検証版は独立な元の再生でリンク・表示・合法性・操作列・ラベルを照合。\n\nログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
