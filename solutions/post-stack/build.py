from pathlib import Path
p=Path(__file__).resolve().parent;s=Path('solutions/stay-cover/main.cpp').read_text()
s=s.replace('    static inline int post_rewrite_mode=5;', '''    static inline int post_rewrite_mode=5;
    static inline int post_stack_mode=0;
    long long stack_rewrite_trials=0,stack_rewrite_accepts=0;''')
needle='''        delete_singles();
        post_saved += int(input_ops.size()) - int(best_ops.size());'''
assert needle in s
new='''        // Two old extras can mask each other's wrong handles. Reposition
        // their existing return operations as a stack, then omit handle digs
        // made unnecessary by that stack. Full replay checks every move.
        if(post_stack_mode){
            auto chosen=edits;
            const int dedicated=ded[u];
            const u64 holes=handle_bits(hmask&~paper[dedicated].opaque);
            const u64 target=handle_bits(A[u]);
            for(int i=0;i<int(edits.size());i++)for(int j=i+1;j<int(edits.size());j++){
                int x=edits[i].paper,y=edits[j].paper;
                if(x==y||!initial_extra[x]||!initial_extra[y]||col_of[x]<0||col_of[y]<0)continue;
                for(int direction=0;direction<2;direction++){
                    int upper=direction?y:x,lower=direction?x:y;
                    u64 covered=(h_opq[upper]|h_opq[lower])&holes;
                    u64 displayed=h_blk[upper]|(h_blk[lower]&~h_opq[upper]);
                    u64 wrong=covered&(displayed^target);
                    int lo=wrong?64-__builtin_clzll(wrong):0;
                    int hi=std::min(col_of[x],col_of[y]);
                    for(int level=lo;level<=hi;level++){
                        if(level>lo&&!(covered>>level&1))continue;
                        u64 repaired=covered&~low_bits(level);
                        std::vector<int> removable;
                        for(int t=0;t<int(edits.size());t++){
                            int k=edits[t].paper,c=col_of[k];
                            if(t==i||t==j||c<0||initial_extra[k]||k==dedicated)continue;
                            if((repaired>>c&1)&&((h_blk[k]^target)>>c&1))removable.push_back(t);
                        }
                        if(removable.size()<2)continue;
                        std::vector<int> ord=initial.order;
                        for(int t=0;t<i;t++){
                            auto[k,a]=edits[t];ord.erase(std::find(ord.begin(),ord.end(),k));
                            int at=a<0?0:int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;ord.insert(ord.begin()+at,k);
                        }
                        int anchor=-1;
                        for(int k:ord){
                            if(k==x||k==y)continue;
                            if(col_of[k]>=level&&!initial_extra[k])break;
                            anchor=k;
                        }
                        auto attempt=[&](const std::vector<int>&removed){
                            auto trial=edits;
                            trial[i].anchor=anchor;trial[j].anchor=direction?anchor:upper;
                            for(int t=int(removed.size())-1;t>=0;t--)trial.erase(trial.begin()+removed[t]);
                            stack_rewrite_trials++;
                            if(evaluate(trial)){chosen=anchorize(best_ops);stack_rewrite_accepts++;}
                        };
                        attempt(removable);
                        if(post_stack_mode>=2&&removable.size()>2)for(int a=0;a<int(removable.size());a++)for(int b=a+1;b<int(removable.size());b++)attempt({removable[a],removable[b]});
                    }
                }
            }
            edits=std::move(chosen);
        }
        delete_singles();
        post_saved += int(input_ops.size()) - int(best_ops.size());'''
s=s.replace(needle,new)
s=s.replace('std::cerr << "rewrite_accepts = "', 'std::cerr << "stack_rewrite_trials = " << solver.stack_rewrite_trials << "\\nstack_rewrite_accepts = " << solver.stack_rewrite_accepts << \'\\n\';\n    std::cerr << "rewrite_accepts = "') if 'std::cerr << "rewrite_accepts = "' in s else s
(p/'main.cpp').write_text(s)
s=Path('solutions/stay-value/probe.cpp').read_text();s=s.replace(' for(auto[stay,cover]:std::array<std::pair<double,double>,7>{{{0,0},{.5,0},{1,0},{0,.25},{0,.5},{.25,.25},{.5,.5}}}) {\n  Solver::stay_strength=stay;Solver::cover_strength=cover;', ' for(int setting=0;setting<3;setting++) {\n  Solver::post_stack_mode=setting;')
s=s.replace('<<",\\\"stay\\\":"<<stay<<",\\\"cover\\\":"<<cover', '<<",\\\"trials\\\":"<<s.stack_rewrite_trials<<",\\\"accepts\\\":"<<s.stack_rewrite_accepts')
(p/'probe.cpp').write_text(s)
s=Path('solutions/stay-value/run.py').read_text().replace('range(56,88)','range(24,56)').replace('ahc074-stay-value','ahc074-post-stack').replace('range(1,7)','range(1,3)');(p/'run.py').write_text(s)
(p/'README.md').write_text('''# 前の穴埋め紙2枚を重ねて列の修正を省く\n\n改良元: solutions/stay-cover。\n\n後処理で、前の商品紙・穴埋め紙のうち2枚の返却操作を変更し、同じ深さへ上下に重ねる。下の紙の誤色を上の紙が隠す組合せなら、単独では使えない位置でも複数の窓を正しく覆える。既存の操作列から、その被覆で不要になる列の色合わせを2操作以上まとめて消す。\n\n候補は下から見える色が全て正しい位置だけとし、削除は対象窓で誤色を持つ通常の列紙の操作だけに限る。全候補の最終表示、全操作の可視性、最後の紙の分類と費用を元の後処理と同じ方法で検査する。削除可能な全操作だけを消す版と、2操作ずつの組合せも試す版を比較する。\n\n研究用。main.cppのpost_stack_mode=0は基準。probe.cppが変更を有効にし、保存設計・固定乱数の独立模擬注文で比較する。隠された注文を使わず、CLOCK_SCALEを適用する。\n''')
