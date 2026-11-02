from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'research.cpp').read_text()
method=r'''
    int cap_tried=0, cap_repaired=0, cap_accepted=0, cap_swapped_units=0;
    double cap_model_gain=0;
    // Exchange a handle with the selector. Repair pairs that disagree on the
    // new handle by swapping whole papers with another column. Every accepted
    // state keeps both colors in every column and preserves generic feasibility.
    void cap_descent(std::vector<int>& permutation) {
        static_assert(kCaps==1 && kCapWidth==1);
        const auto old_A=A, old_hb=hb;
        const auto old_unit=unit;
        const double old_cost=cur;
        double best_cost=cur;
        int best_j=-1, best_repairs=0;
        std::vector<Unit> best_unit;
        for(int j=0;j<H;++j) {
            ++cap_tried;
            A=old_A; hb=old_hb; unit=old_unit;
            const int w=handle[j];
            for(int t=0;t<P;++t) {
                const u64 flip=((A[t]>>w)^(A[t]>>kCapWindow))&1;
                A[t]^=((1ULL<<w)|kCapBit)*flip;
                hb[t]^=(1ULL<<j)*flip;
            }
            rebuild();
            int repaired=0;
            bool success=true;
            auto swap_units=[&](int x,int y) {
                update(unit[x],-1); update(unit[y],-1);
                std::swap(unit[x].c,unit[y].c);
                update(unit[x],1); update(unit[y],1);
            };
            for(int pass=0;pass<2 && success;++pass) {
                // First repair all disagreeing pairs; then (if needed) restore
                // the second color of the newly assigned handle column.
                for(int x=0;x<U;++x) {
                    if(unit[x].c!=j)continue;
                    const bool bad_pair=!valid(unit[x],j);
                    const bool monochrome=(n1[j]==0 || n1[j]==nc[j]);
                    if(pass==0 ? !bad_pair : !monochrome)continue;
                    double best_delta=1e100; int by=-1;
                    const double before=cur;
                    for(int y=0;y<U;++y) {
                        const int c=unit[y].c;
                        if(c==j || !valid(unit[x],c) || !valid(unit[y],j))continue;
                        if(pass==1 && color(unit[y],j)==color(unit[x],j))continue;
                        swap_units(x,y);
                        const bool two_colors=n1[c]>0 && n1[c]<nc[c];
                        if(two_colors && cur-before<best_delta)best_delta=cur-before,by=y;
                        swap_units(x,y);
                    }
                    if(by<0){success=false;break;}
                    swap_units(x,by); ++repaired;
                }
            }
            for(const auto& u:unit)success&=valid(u,u.c);
            for(int c=0;c<H;++c)success&=n1[c]>0 && n1[c]<nc[c];
            if(success) {
                cap_repaired+=repaired>0;
                if(cur<best_cost-1e-7) {
                    best_cost=cur;best_j=j;best_unit=unit;best_repairs=repaired;
                }
            }
        }
        A=old_A;hb=old_hb;unit=old_unit;
        if(best_j>=0) {
            const int w=handle[best_j];
            for(int t=0;t<P;++t) {
                const u64 flip=((A[t]>>w)^(A[t]>>kCapWindow))&1;
                A[t]^=((1ULL<<w)|kCapBit)*flip;
                hb[t]^=(1ULL<<best_j)*flip;
            }
            unit=best_unit;
            std::swap(permutation[w],permutation[kCapWindow]);
            ++cap_accepted;cap_model_gain+=old_cost-best_cost;cap_swapped_units+=best_repairs;
        }
        rebuild();
    }
'''
s=s.replace('    static constexpr int kAnnealSegments = 4;',method+'\n    static constexpr int kAnnealSegments = 4;')
s=s.replace('void anneal(double seconds, int fixedIterations = 0)', 'void anneal(double seconds, int fixedIterations, std::vector<int>& permutation)')
s=s.replace('            total += anneal_iters;', '            total += anneal_iters;\n            if(s+1<kAnnealSegments)cap_descent(permutation);')
s=s.replace('des->anneal(1e9, anneal_iters);','des->anneal(1e9, anneal_iters, permutation);')
s=s.replace('des->anneal(std::max(0.005, kAnnealEnd - elapsed_sec()), 0);','des->anneal(std::max(0.005, kAnnealEnd - elapsed_sec()), 0, permutation);')
s=s.replace('    // Restore the cap bit only for the physical papers and online targets.', '''    A=des->A;
    std::cerr<<"cap_tried = "<<des->cap_tried<<"\\ncap_repaired = "<<des->cap_repaired
             <<"\\ncap_accepted = "<<des->cap_accepted<<"\\ncap_swapped_units = "<<des->cap_swapped_units
             <<"\\ncap_model_gain = "<<des->cap_model_gain/P<<'\\n';
    // Restore the cap bit only for the physical papers and online targets.''')
(r/'repair.cpp').write_text(s)
(r/'work/repair-README.md').write_text('''# astra-cap2: キャップ窓交換と列修復\n\n改良元: `solutions/as6-cap38`。\n\n汎用紙 6 枚・汎用窓 38・1 窓キャップ・25 列を維持する。設計焼きなましの各区間の間でキャップと各ハンドル窓を交換する候補を調べる。新しいハンドルで不一致となる共有紙は、別列の紙と交換して修復する。列ごとの白黒両色と比較器の整合を守った候補のうち、列・穴・汎用層の合計模型が最も下がるものを採用する。\n\nPR 78 の cap-joint が交換前に棄却した「新ハンドルで対が異色」の場合も調べる。最終比較と採否は `REPORT.md` に記す。\n\n設計の時間配分は基準どおり。補助表の打ち切りは 1.48 秒、簡易注文処理への切り替えは 1.68 秒（いずれも CLOCK_SCALE 込み）。`cap_tried` は窓交換候補数、`cap_repaired` は紙交換によって修復できた候補数、`cap_accepted` は採用回数、`cap_swapped_units` は採用した修復の紙交換回数、`cap_model_gain` はその時点の模型改善量の合計 / 256。\n''')
