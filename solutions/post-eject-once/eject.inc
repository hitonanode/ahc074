        if(mid_eject_mode&&edits.size()>=2){
            const auto base_edits=edits;
            std::array<bool,K>possible{};
            for(auto e:base_edits)possible[e.paper]=true;
            u64 blocked=0;
            // Relative order of all unmoved papers is invariant. An unmoved
            // paper covered by earlier unmoved papers can never be selected.
            for(int k:initial.order)if(!possible[k]){
                if(paper[k].opaque&~blocked)possible[k]=true;
                blocked|=paper[k].opaque;
            }
            std::vector<int>candidates;
            for(int k=0;k<K;k++)if(k!=kCapPaper&&(!mid_possible||possible[k]))candidates.push_back(k);
            for(int j=int(base_edits.size())-1;j>=1;j--)for(int i=j-1;i>=0;i--){
                int pi=base_edits[i].paper,pj=base_edits[j].paper;
                if(mid_filter>=1&&(pi<M||pj<M||pi==ded[u]||pj==ded[u]))continue;
                if(mid_filter>=2&&(initial_extra[pi]||initial_extra[pj]))continue;
                auto trial=base_edits;trial.erase(trial.begin()+j);trial.erase(trial.begin()+i);
                int length=trial.size();std::vector<int>ord=initial.order;
                std::vector<std::array<u64,3>>visible_at(length+1);
                int first_illegal=length;
                bool visibility_ready=false;
                auto prepare_visibility=[&]{
                    if(visibility_ready)return;
                    visibility_ready=true;auto prefix=initial.order;
                    for(int t=0;t<=length;t++){
                        u64 covered=0;
                        for(int k:prefix){if(paper[k].opaque&~covered)visible_at[t][k>>6]|=1ULL<<(k&63);covered|=paper[k].opaque;}
                        if(t==length)break;
                        auto[k,a]=trial[t];int pos=std::find(prefix.begin(),prefix.end(),k)-prefix.begin();
                        int dest=a<0?0:int(std::find(prefix.begin(),prefix.end(),a)-prefix.begin())+1;if(pos<dest)dest--;
                        if(dest!=pos&&!(visible_at[t][k>>6]>>(k&63)&1))first_illegal=std::min(first_illegal,t);
                        prefix.erase(prefix.begin()+pos);prefix.insert(prefix.begin()+dest,k);
                    }
                };
                if(mid_fast){
                    auto next=initial_next,prev=initial_prev;
                    for(auto[k,anchor]:trial){
                        int a=anchor<0?root:anchor;if(prev[k]==a)continue;
                        next[prev[k]]=next[k];prev[next[k]]=prev[k];
                        int b=next[a];next[a]=k;prev[k]=a;next[k]=b;prev[b]=k;
                    }
                    ord.clear();for(int k=next[root];k!=root;k=next[k])ord.push_back(k);
                }else{
                // These states ignore later illegality only to find candidates.
                // A repair is always inserted before the first illegal edit.
                for(int t=0;t<=length;t++){
                    u64 covered=0;
                    for(int k:ord){if(paper[k].opaque&~covered)visible_at[t][k>>6]|=1ULL<<(k&63);covered|=paper[k].opaque;}
                    if(t==length)break;
                    auto[k,a]=trial[t];int pos=std::find(ord.begin(),ord.end(),k)-ord.begin();
                    int dest=a<0?0:int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;if(pos<dest)dest--;
                    if(dest!=pos&&!(visible_at[t][k>>6]>>(k&63)&1))first_illegal=std::min(first_illegal,t);
                    ord.erase(ord.begin()+pos);ord.insert(ord.begin()+dest,k);
                }
                    visibility_ready=true;
                }
                mid_pairs++;
                std::array<int,64>first,second;first.fill(K);second.fill(K);
                std::array<u64,K>owned{};u64 covered=0,twice=0,shown=0,second_black=0;
                for(int t=0;t<K;t++){
                    int k=ord[t];u64 two=paper[k].opaque&covered&~twice,one=paper[k].opaque&~covered;
                    second_black|=paper[k].black&two;owned[k]=one;shown|=paper[k].black&one;
                    for(u64 z=two;z;z&=z-1)second[__builtin_ctzll(z)]=t;
                    for(u64 z=one;z;z&=z-1)first[__builtin_ctzll(z)]=t;
                    covered|=paper[k].opaque;twice|=two;if(twice==~u64(0))break;
                }
                if(__builtin_popcountll(shown^A[u])<2)continue;
                for(int k:candidates){
                    u64 after=shown^((shown^second_black)&owned[k]),bad=after^A[u];
                    u64 wrong=paper[k].opaque&(paper[k].black^A[u]);
                    if(!bad||(bad&~paper[k].opaque)||(bad&wrong))continue;
                    int pos=std::find(ord.begin(),ord.end(),k)-ord.begin(),lo=0,hi=K-1;
                    auto without_pos=[&](int w){int p=first[w]==pos?second[w]:first[w];return p-int(p>pos);};
                    for(u64 z=bad;z;z&=z-1)hi=std::min(hi,without_pos(__builtin_ctzll(z)));
                    for(u64 z=wrong;z&&lo<=hi;z&=z-1)lo=std::max(lo,without_pos(__builtin_ctzll(z))+1);
                    if(lo>hi)continue;
                    auto without=ord;without.erase(without.begin()+pos);std::vector<int>anchors;
                    auto add=[&](int gap){if(gap<lo||gap>hi||gap==pos)return;int a=gap?without[gap-1]:-1;if(std::find(anchors.begin(),anchors.end(),a)==anchors.end())anchors.push_back(a);};
                    add(lo);add(hi);
                    std::array<bool,64>seen{};
                    for(int t=0;t<K-1;t++){
                        int c=col_of[without[t]];
                        if(c<0)add(t),add(t+1);
                        else if(!seen[c]){seen[c]=true;if(c<=col_of[k])add(t);}
                        if(c==col_of[k])add(t),add(t+1);
                    }
                    prepare_visibility();
                    for(int t=mid_eject_mode==1?length:0;t<=first_illegal;t++){
                        if(!(visible_at[t][k>>6]>>(k&63)&1))continue;
                        for(int a:anchors){
                            auto next=trial;next.insert(next.begin()+t,{k,a});mid_trials++;
                            double before_score=best_score;
                            if(evaluate(next)){
                                mid_accepts++;mid_inside+=t<length;
                                auto kind=[&](int x){return x<M?0:x==ded[u]?1:x==initial.top_d?2:initial_extra[x]?3:4;};
                                int a=kind(base_edits[i].paper),b=kind(base_edits[j].paper);if(a>b)std::swap(a,b);
                                int category=(a*5+b)*5+kind(k);eject_gain[category]+=before_score-best_score;eject_count[category]++;
                                int x=base_edits[i].paper,y=base_edits[j].paper;
                                int relation=(k==x||k==y)|((col_of[x]==col_of[y])<<1)|((col_of[x]==col_of[ded[u]]||col_of[y]==col_of[ded[u]])<<2)|((col_of[k]==col_of[ded[u]])<<3);
                                for(auto e:trial)if(e.paper==k){relation|=16;break;}
                                if(t<i)relation|=32;
                                relation_gain[relation]+=before_score-best_score;relation_count[relation]++;
                            }
                        }
                    }
                }
            }
            edits=anchorize(best_ops);
        }
