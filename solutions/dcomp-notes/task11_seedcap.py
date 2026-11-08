from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-seed-one/main.cpp').read_text()
def rep(s,a,b):assert s.count(a)==1,(s.count(a),a[:100]);return s.replace(a,b)
for cap in [1,2]:
 s=rep(B,'if (neutral_candidates.size() > size_t(neutral_width)) neutral_candidates.pop_back();',f'if (neutral_candidates.size() > size_t(secondary_neutral?{cap}:neutral_width)) neutral_candidates.pop_back();')
 s=rep(s,'''                        neutral_collect=true;secondary_neutral=true;
                        second_path=post_optimize''','''                        auto primary_pool=std::move(neutral_candidates);neutral_candidates.clear();
                        neutral_collect=true;secondary_neutral=true;
                        second_path=post_optimize''')
 s=rep(s,'''                        neutral_collect=false;secondary_neutral=false;
                        const double second_value''','''                        neutral_collect=false;secondary_neutral=false;
                        auto secondary_pool=std::move(neutral_candidates);neutral_candidates=std::move(primary_pool);
                        for(auto& nc:secondary_pool) {
                            auto it=std::find_if(neutral_candidates.begin(),neutral_candidates.end(),
                                [&](const auto& old){return old.signature==nc.signature;});
                            if(it==neutral_candidates.end())neutral_candidates.push_back(std::move(nc));
                            else if(nc.value<it->value)*it=std::move(nc);
                        }
                        std::sort(neutral_candidates.begin(),neutral_candidates.end(),[&](const auto& a,const auto& b){
                            if(cfg.candidate_priority) {
                                if(a.path.size()!=b.path.size())return a.path.size()<b.path.size();
                                if(cfg.hidden_rank && a.hides!=b.hides)return a.hides>b.hides;
                                if(a.repeats!=b.repeats)return a.repeats>b.repeats;
                            }
                            return a.value<b.value;
                        });
                        const char* width_setting=search_env("NEUTRAL_WIDTH");
                        const int merged_width=width_setting?std::max(1,std::atoi(width_setting)):2;
                        if(neutral_candidates.size()>size_t(merged_width))neutral_candidates.resize(merged_width);
                        const double second_value''')
 d=R/'solutions'/f'dcomp-t11-seedone-cap{cap}';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-seed-one\n\n追加親の1→1列挙では、元の親の候補poolを退避し、追加親の上位'+str(cap)+'候補だけを記録する。署名を重複除去して元のpoolと合わせ、同じpriorityで元のNEUTRAL_WIDTH枠へ戻す。追加親の直接改善はそのまま採る。\n\n一要求の本修復数を状態・固定件数で抑え、時刻は使わない。両コンパイラ同設定、他の予算・設計・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
