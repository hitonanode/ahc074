from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-links/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100]);s=s.replace(a,b)
sub('    struct AnchorScreen {\n        Links next, prev;', '''    struct AnchorScreen {
        struct ReplayStep { int paper, depth, cutoff; OP_TAG(uint8_t tag;) };
        bool replay_ready=false, replay_ok=false, k_visible=false;
        int old_prev=-1, minimum_rank=-2;
        std::array<int,K+1> stable_rank, before_stable;
        ByteOrder final_without;
        Moves prefix_path;
        OP_TAG(std::vector<uint8_t> prefix_tags;)
        std::vector<ReplayStep> steps;
        Links next, prev;''')
sub('            S.active = false;\n            if (!post_context.masks_exact)', '            S.active = false;\n            S.replay_ready = false;\n            if (!post_context.masks_exact)')
needle='        // Only a successful, exact anchor screen may supply the final links.\n'
new='''        // Eligible anchors are never moved or used by later edits. Their order stays
        // fixed. Remove k at edit i and replay G once: each later edit's depth gets
        // +1 exactly when the chosen anchor precedes its anchor in that stable order.
        // If all visible windows of a later moved paper belong to k, k must be below
        // that paper. All such legality conditions reduce to one minimum stable rank.
        auto prepare_screen_replay = [&]() {
            auto& S=anchor_screen;
            if(S.replay_ready)return;
            S.replay_ready=true;S.replay_ok=false;S.minimum_rank=-2;
            S.prefix_path.clear();OP_TAG(S.prefix_tags.clear();) S.steps.clear();
            ByteOrder o=initial_bytes;
            std::array<u64,K+1> cov;cov[0]=0;int valid=0;
            auto visible=[&](int k,int p) {
                for(;valid<p;++valid)cov[valid+1]=cov[valid]|paper[o[valid]].opaque;
                return paper[k].opaque&~cov[p];
            };
            for(int t=0;t<S.i;++t)if(t!=S.j) {
                const auto& e=edits[t];int p=find_paper(o,e.paper);
                int d=e.anchor<0?0:find_paper(o,e.anchor)+1;d-=p<d;
                if(p==d)continue;
                if(!visible(e.paper,p))return;
                shift_byte(o,p,d);valid=std::min(valid,std::min(p,d));
                S.prefix_path.push_back({e.paper,d});OP_TAG(S.prefix_tags.push_back(e.tag);)
            }
            const int kp=find_paper(o,S.k);
            S.k_visible=visible(S.k,kp)!=0;S.old_prev=kp?o[kp-1]:-1;
            // Keep k at the unused last slot of this 191-paper replay.
            shift_byte(o,kp,K-1);valid=0;
            int last=-1;
            for(int i=0;i<K-1;++i) {
                const int x=o[i];S.stable_rank[x]=i;S.before_stable[x]=last;
                if(S.blocked[x]!=S.epoch)last=i;
            }
            S.stable_rank[root]=-1;S.before_stable[root]=-2;
            for(int t=S.i+1;t<int(edits.size());++t)if(t!=S.j) {
                const auto& e=edits[t];const int x=e.paper,b=e.anchor;
                const int p=find_paper(o,x);
                int d=b<0?0:find_paper(o,b)+1;d-=p<d;
                if(p==d)continue;
                const u64 vis=visible(x,p);
                if(!vis)return;
                if(!(vis&~paper[S.k].opaque))S.minimum_rank=std::max(S.minimum_rank,S.before_stable[x]);
                const int cutoff=b<0?-2:S.before_stable[b];
                S.steps.push_back({x,d,cutoff OP_TAG(,e.tag)});
                shift_byte(o,p,d);valid=std::min(valid,std::min(p,d));
                S.before_stable[x]=b<0?-1:S.before_stable[b];
            }
            S.final_without=o;S.replay_ok=true;
        };
'''
assert s.count(needle)==1;s=s.replace(needle,new+needle)
start='''                int cover_valid = 0;
                cover[0] = 0;

                int common = 0;'''
new='''                if(use_screen) {
                    prepare_screen_replay();
                    const auto& S=anchor_screen;
                    const int a=screened_anchor,rank=a<0 || !S.replay_ok?-1:S.stable_rank[a];
                    const bool legal=S.replay_ok && (S.k_visible || a==S.old_prev) && rank>S.minimum_rank;
                    if(legal) {
                        path=S.prefix_path;OP_TAG(path_tags=S.prefix_tags;)
                        if(a!=S.old_prev) {
                            path.push_back({S.k,rank+1});OP_TAG(path_tags.push_back(edits[S.i].tag);)
                        }
                        for(const auto& step:S.steps) {
                            path.push_back({step.paper,step.depth+int(rank<=step.cutoff)});
                            OP_TAG(path_tags.push_back(step.tag);)
                        }
                        ord=S.final_without;
                        const int d=a<0?0:find_paper(ord,a)+1;
                        shift_byte(ord,K-1,d);
                    }
#ifdef SCREEN_REPLAY_CHECK
                    {
                        ByteOrder ref=initial_bytes;Moves ref_path;
                        OP_TAG(std::vector<uint8_t> ref_tags;)
                        bool ok=true;
                        for(const auto& e:trial) {
                            const int p=find_paper(ref,e.paper);
                            int d=e.anchor<0?0:find_paper(ref,e.anchor)+1;d-=p<d;
                            if(p==d)continue;
                            u64 cv=0;for(int t=0;t<p;++t)cv|=paper[ref[t]].opaque;
                            if(!(paper[e.paper].opaque&~cv)){ok=false;break;}
                            shift_byte(ref,p,d);ref_path.push_back({e.paper,d});OP_TAG(ref_tags.push_back(e.tag);)
                        }
                        if(ok!=legal || (ok && (ref!=ord || ref_path!=path OP_TAG(||ref_tags!=path_tags)))) {
                            std::cerr<<"SCREEN_REPLAY_MISMATCH "<<S.i<<' '<<S.j<<' '<<a<<' '<<ok<<' '<<legal<<'\\n';
                            std::abort();
                        }
                    }
#endif
                    if(!legal)return false;
                } else {
                int cover_valid = 0;
                cover[0] = 0;

                int common = 0;'''
sub(start,new)
sub('''                remember(trial.size());
                // Preserve the invariant''','''                remember(trial.size());
                }
                // Preserve the invariant''')
for name,extra in [('dcomp-screen-replay',''),('dcomp-screen-replay-check','#define SCREEN_REPLAY_CHECK 1\n#define SCREEN_LINK_CHECK 1\n')]:
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(extra+s)
 (p/'README.md').write_text('''改良元: solutions/dcomp-screen-links

可換な付け替え候補では、対象紙kを除いた191枚の並びGを一度だけ再生する。候補anchorは後続操作で動かず、anchorとしても使われないので、その相対順は固定。後続の移動する紙がGで見える窓をkだけで覆われる場合、kはその紙より下に置く必要がある。この条件を候補anchorの順位の下限にまとめる。

後続操作の挿入深さは、Gでの深さに「kがそのanchorより上にある」場合だけ1を加えたもの。既存のscreenが可換性と表示を保証する候補だけにこの再生を使い、それ以外は元の再生を使う。最終のcap検査、canonicalize、費用、候補の選択は元と同じ。SCREEN_REPLAY_CHECKでは全試行を元の紙配列でも再生し、合法性・最終配列・操作列・ラベルを完全比較する。予算固定、時間fallbackなし。
''')
