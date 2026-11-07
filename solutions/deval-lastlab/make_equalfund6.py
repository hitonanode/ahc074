from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper3-eq1/main.cpp').read_text()
s=s.replace('if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";','if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "4";')
a='''                        (cfg.plan_shortlist == 3 && c.path.size() == chosen_path.size()))) {'''
b='''                        ((cfg.plan_shortlist == 3 || cfg.plan_shortlist >= 4) && c.path.size() == chosen_path.size()) || ((cfg.plan_shortlist == 5 || (cfg.plan_shortlist == 4 && repeated) || (cfg.plan_shortlist == 6 && c.cost <= baseline_value + 1.5)) && c.path.size() == chosen_path.size()+1))) {'''
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace('int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 3 : 0);','int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 6 : 0);')
a='rematch_probability(*des, extra?1:2, 1.0, 2.0);';assert s.count(a)==1;s=s.replace(a,'rematch_probability(*des, 1, 1.0, 2.0);')
p=root/'solutions/deval-equalfund6';p.mkdir();(p/'main.cpp').write_text(s);assert len(s.encode())<=522000
(p/'README.md').write_text('''改良元: `solutions/deval-helper3-eq1`（flex125-plan3系列）。

最初の4枝の穴あけ前rematchを2回から1回へ減らし、注文の候補に時間を回す。単独helperはgeneric移動数が通常と同じ候補を見積り上位1件まで許し、移動数を減らす候補と合わせて上位3件を計画する。generic goalの同距離は既存のfutureが小さい方を選ぶ。

注文のneutral rewriteの幅を3から4に増やす。PLAN_SHORTLIST=6を追加し、現計画以下の手数のほか、1手長くてもraw plan_costの差が1.5以下なら追加後処理する。既存モード0–5も保つ。NS_ROUNDS=2、完成8設計、窓割当てと焼きなましの反復数は同じ。時計による打切りや軽量化はしない。DesignStoreは選んだ設計を保存する。

元の統計・@paper/@ops・trace・profiler・実験switch・段の目次を保つ。dv_candidatesとdv_chosenは設計選択、dv_finish_secは全仕上げ累計、req_secは注文処理時間。容量を確保するための未使用関数・旧MDP分類・コメント整理はtrim6bを引き継ぐ。
''');print(len(s.encode()))
