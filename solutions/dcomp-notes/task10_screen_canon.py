from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(a[:100],s.count(a));s=s.replace(a,b)
sub('        ByteOrder final_without;','''        ByteOrder final_without;
        bool canon_ready=false;
        std::array<int,K+1> final_pos, suffix_col;
        std::array<u64,3> outside;
        std::array<std::array<u64,3>,65> higher;
        std::array<u64,K+1> deep_prefix;
        u64 nonempty;''')
sub('            S.replay_ready = false;','            S.replay_ready = false; S.canon_ready=false;')
needle='        // Only a successful, exact anchor screen may supply the final links.\n'
code='''        // Canonical records for G plus one insertion. A column paper is in place
        // iff its column does not exceed the suffix minimum (generic sheets use -1).
        // Inserting k can only evict in-place papers above it in deeper columns.
        auto canonicalize_screen = [&](int anchor) {
            auto& S=anchor_screen;
            if(!S.canon_ready) {
                S.canon_ready=true;S.outside={};S.nonempty=0;
                for(auto& bits:S.higher)bits={};
                S.deep_prefix.fill(0);
                int cur=H;
                for(int p=K-2;p>=0;--p) {
                    const int x=S.final_without[p],c=col_of[x];
                    S.final_pos[x]=p;S.suffix_col[p]=cur;
                    if(c>=0) {
                        if(c<=cur) {
                            cur=c;S.higher[c][p>>6]|=1ULL<<(p&63);
                            if(!(S.nonempty>>c&1))S.deep_prefix[p+1]|=1ULL<<c;
                            S.nonempty|=1ULL<<c;
                        } else S.outside[p>>6]|=1ULL<<(p&63);
                    } else if(x<M)cur=-1;
                }
                S.suffix_col[K-1]=H;
                for(int p=1;p<K;++p)S.deep_prefix[p]|=S.deep_prefix[p-1];
                for(int c=H-1;c>=0;--c)for(int w=0;w<3;++w)S.higher[c][w]|=S.higher[c+1][w];
            }
            const int k=S.k,c=col_of[k],gap=anchor<0?0:S.final_pos[anchor]+1;
            const int inserted=c>=0?c:(k<M?-1:H);
            const int below=gap==K-1?H:S.suffix_col[gap];
            // suffix_col[gap] excludes G[gap]; include it for k's suffix.
            int after=below;
            if(gap<K-1) {
                const int x=S.final_without[gap],cc=col_of[x];
                if(cc>=0)after=std::min(after,cc);else if(x<M)after=-1;
            }
            u64 present=S.nonempty & ~(S.deep_prefix[gap] & ~low_bits(std::max(0,inserted+1)));
            const bool k_out=c>=0 && c>after;
            if(c>=0 && !k_out)present|=1ULL<<c;
            std::array<u64,3> outside=S.outside;
            for(int w=0;w<3;++w) {
                const int n=std::clamp(gap-64*w,0,64);
                outside[w]|=S.higher[std::clamp(inserted+1,0,H)][w]&low_bits(n);
            }
            int ntop=-1,nf_count=0;
            std::array<Filler,K> nf;
            auto add=[&](int x,int p,int level) {
                const int pos=p+(p>=gap);
                if(pos==0 || (pos==1 && order[0]==kCapPaper)){ntop=x;return;}
                const u64 prior=present&low_bits(std::max(0,level));
                const int lvl=prior?64-__builtin_clzll(prior):0;
                nf[nf_count++]={x,lvl,col_of[x]};
            };
            // Enumerate the small out-of-column set in final stack order.
            bool inserted_out=false;
            auto add_k=[&] {
                inserted_out=true;
                if(!k_out)return;
                if(gap==0 || (gap==1 && order[0]==kCapPaper)){ntop=k;return;}
                const u64 prior=present&low_bits(std::max(0,after));
                nf[nf_count++]={k,prior?64-__builtin_clzll(prior):0,c};
            };
            for(int w=0;w<3;++w)for(u64 bits=outside[w];bits;bits&=bits-1) {
                const int p=64*w+__builtin_ctzll(bits);
                if(!inserted_out && gap<=p)add_k();
                const int level=p<gap?std::min(S.suffix_col[p],inserted):S.suffix_col[p];
                add(S.final_without[p],p,level);
            }
            if(!inserted_out)add_k();
            unsigned epoch=(canonical_epoch+=2);
            if(!epoch){canonical_stamp.fill(0);canonical_epoch=epoch=2;}
            for(int i=0;i<nf_count;++i){canonical_index[nf[i].paper]=i;canonical_stamp[nf[i].paper]=epoch;}
            std::array<Filler,2*K> res;int count=0;
            for(const auto& f:fillers)if((canonical_stamp[f.paper]&~1U)==epoch) {
                res[count++]=nf[canonical_index[f.paper]];canonical_stamp[f.paper]=epoch|1U;
            }
            for(int i=0;i<nf_count;++i)if(canonical_stamp[nf[i].paper]==epoch)res[count++]=nf[i];
            top_d=ntop;fillers.assign(res.begin(),res.begin()+count);
        };
'''
assert s.count(needle)==1;s=s.replace(needle,code+needle)
sub('''                fillers = seed.fillers;
                canonicalize();
                const bool reachable''','''                fillers = seed.fillers;
                if(use_screen) {
                    canonicalize_screen(screened_anchor);
#ifdef SCREEN_CANON_CHECK
                    const auto fast_top=top_d;const auto fast_fillers=fillers;
                    top_d=seed.top_d;fillers=seed.fillers;canonicalize();
                    bool same=top_d==fast_top && fillers.size()==fast_fillers.size();
                    for(int i=0;same && i<int(fillers.size());++i)
                        same=fillers[i].paper==fast_fillers[i].paper && fillers[i].lvl==fast_fillers[i].lvl && fillers[i].hi==fast_fillers[i].hi;
                    if(!same){std::cerr<<"SCREEN_CANON_MISMATCH "<<anchor_screen.k<<' '<<screened_anchor<<'\\n';std::abort();}
#endif
                } else canonicalize();
                const bool reachable''')
for check in [False,True]:
 p=r/'solutions'/('dcomp-screen-canon'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define SCREEN_CANON_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n可換な付け替えの最終並びGについて、列番号のsuffix最小値、列内の紙の位置bitset、最下部の位置を共有する。1枚挿入で列外に出るのは、挿入位置より上かつ挿入紙より深い列の紙だけ。この集合を列挙してcanonical recordsを復元し、旧fillersの優先順位も維持する。検証版では各shortcutを元のcanonicalizeと比較する。\n\n予算・モデル値・合法性・選択順は不変。ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
