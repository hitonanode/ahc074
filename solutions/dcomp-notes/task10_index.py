from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-combo-ten/main.cpp').read_text()
a=s.index('                    std::sort(neutral_candidates.begin(), neutral_candidates.end(),\n')
b=s.index('                    if (neutral_candidates.size() > size_t(neutral_width))',a)
old=s[a:b];body=old[old.index('                              [&](const auto& a, const auto& b) {'):]
assert body.endswith('                              });\n')
body=body.replace('                              });\n','                              };\n')
new='''                    // Sort the same keys in the same order, moving indices first.
                    // The common already-sorted case moves no large State/path records.
                    const auto candidate_less =
'''+body+'''                    if(neutral_candidates.size()<=64) {
                        std::array<size_t,64> permutation;
                        const size_t n=neutral_candidates.size();
                        std::iota(permutation.begin(),permutation.begin()+n,size_t(0));
                        std::sort(permutation.begin(),permutation.begin()+n,[&](size_t i,size_t j){
                            return candidate_less(neutral_candidates[i],neutral_candidates[j]);
                        });
                        for(size_t i=0;i<n;++i)if(permutation[i]!=i) {
                            auto saved=std::move(neutral_candidates[i]);
                            size_t at=i;
                            while(permutation[at]!=i) {
                                const size_t from=permutation[at];
                                neutral_candidates[at]=std::move(neutral_candidates[from]);
                                permutation[at]=at;at=from;
                            }
                            neutral_candidates[at]=std::move(saved);permutation[at]=at;
                        }
                    } else std::sort(neutral_candidates.begin(),neutral_candidates.end(),candidate_less);
'''
s=s[:a]+new+s[b:]
p=r/'solutions/dcomp-neutral-index';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-combo-ten

中立探索の候補のsortを、同じ比較関数でまずindexに適用し、その置換が変える要素だけに状態のmoveを行う。既に整列済みなら、192枚の並び・補助紙・操作列を含む大きな候補を動かさない。64候補を超える実験設定では元のsortを使う。浮動小数点の採否・候補数・検索順は保つ。ログと実験スイッチ、DesignStoreを維持する。時間fallbackはない。
''')
