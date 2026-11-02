from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'repair.cpp').read_text()
s=s.replace('double best_delta=1e100; int by=-1;', 'double best_delta=1e100; int by=-1;\n                    Unit best_x,best_y;')
s=s.replace('if(two_colors && cur-before<best_delta)best_delta=cur-before,by=y;', 'if(two_colors && cur-before<best_delta){best_delta=cur-before;by=y;best_x=unit[x];best_y=unit[y];}')
needle='''                    if(by<0){success=false;break;}
                    swap_units(x,by); ++repaired;'''
assert needle in s
s=s.replace(needle,r'''                    // Also repair a disagreeing pair by exchanging one target
                    // with its compatible partner's current paper. This changes
                    // the pairing, without forcing the whole pair to a new column.
                    if(pass==0 && unit[x].b>=0) {
                        for(int u=0;u<U;++u) {
                            owner[unit[u].a]=u;
                            if(unit[u].b>=0)owner[unit[u].b]=u;
                        }
                        const Unit ox=unit[x];
                        for(int flip=0;flip<2;++flip) {
                            const int keep=flip?ox.b:ox.a,replace=flip?ox.a:ox.b;
                            for(int other:partners[keep]) {
                                const int y=owner[other];if(y==x)continue;
                                const Unit oy=unit[y];const int c=oy.c;
                                Unit nx=ox,ny=oy;
                                if(flip)nx.a=other;else nx.b=other;
                                if(ny.a==other)ny.a=replace;else ny.b=replace;
                                if(!valid(nx,j)||!valid(ny,c)||(ny.b>=0&&!ok[ny.a][ny.b]))continue;
                                update(ox,-1);update(oy,-1);update(nx,1);update(ny,1);
                                if((c==j||(n1[c]>0&&n1[c]<nc[c])) && cur-before<best_delta) {
                                    best_delta=cur-before;by=y;best_x=nx;best_y=ny;
                                }
                                update(nx,-1);update(ny,-1);update(ox,1);update(oy,1);
                            }
                        }
                    }
                    if(by<0){success=false;break;}
                    update(unit[x],-1);update(unit[by],-1);
                    unit[x]=best_x;unit[by]=best_y;
                    update(unit[x],1);update(unit[by],1); ++repaired;''')
(r/'repair_plus.cpp').write_text(s)
(r/'work/repair-plus-README.md').write_text('''# キャップ窓交換と対の組み替えによる修復\n\n改良元: `solutions/as6-cap38`。\n\n汎用紙 6 枚、汎用窓 38、1 窓キャップ、25 ハンドルを維持する。設計の 4 区間の間に、キャップとハンドルを交換する候補を評価する。新ハンドルで異色となる対は、紙全体を他列の紙と交換するか、対の一方の商品を別の適合商品と交換して修復する。各列の白黒両色、全商品の担当、比較器の整合を維持し、合計設計費用が下がる交換を採用する。\n\n親ディレクトリの候補との差は、紙の交換に加えて商品の組み替えも修復に使う点。パラメータは MAP 0.50 秒、GOPT 0.61 秒、設計 1.305 秒、後処理 1.36 秒、補助表 1.48 秒、簡易処理移行 1.68 秒。時計は CLOCK_SCALE 倍。`cap_model_gain` は採用した窓交換の模型改善量 / 256、`cap_swapped_units` は修復操作の回数。評価結果は親の `REPORT.md`。\n''')
