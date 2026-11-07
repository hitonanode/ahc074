from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
for name,parent in [('deval-flex125','deval-flex8-fast'),('deval-flex125-plan3','deval-flex8-fast-plan3')]:
    s=(R/'solutions'/parent/'main.cpp').read_text()
    old='rematch_probability(*des, late_iterations, 1.05, 2.0, &extra, extra_mode)'
    assert s.count(old)==1;s=s.replace(old,'rematch_probability(*des, late_iterations, 1.25, 2.0, &extra, extra_mode)',1)
    p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/'+parent+'`。\n\n'+
       '穴あけ後の再割当てで、単独紙のハンドル色の固定を解除する。ペアの互換性は保ち、各列に両色が残らない巡回は棄却する。巡回の受理に使うfiller価値の係数を1.05から1.25へ変える。穴あけ前の再割当ては従来通り。完成8候補からVで選ぶ。\n\n'+
       '注文側は、列MDPの4分類を色ごとの実際のfiller込み需要に合う2群へ分け、計画の末端費用に汎用紙の1注文先の平均移動数×0.5を加える。'+
       ('PLAN_SHORTLIST=3で現在と同手数の計画も後処理する。' if 'plan3' in name else 'PLAN_SHORTLIST=2を保つ。')+
       'neutral rewriteは2反復。設計と注文の予算は固定。時間不足による切り替えは設けない。\n\n'+
       '出力を保つ整数累積和・V色比較、列移動の特殊化、V特徴量の参照先の先取り、汎用紙評価のpopcount命令を引き継ぐ。浮動小数点の更新順を保つ。Vの係数表は行頭空白のみ縮め、ログ・注釈・実験スイッチ・プロファイラ・段の目次を保つ。DesignStoreは選んだ最終設計を保存する。\n\n'+
       '主な指標: dv_candidatesは完成候補数、dv_chosenは選んだ候補、dv_anneal_sec/dv_finish_sec/dv_eval_secは各段の累計時間。model_costとd2_model_finalは従来の設計模型、dv_bestは完成設計を選ぶV。colmdp_*は列MDPの規模と被覆、req_sec/end_secは注文処理と全体のCLOCK_SCALE付き時間。\n')
    print(name,len(s.encode()))
