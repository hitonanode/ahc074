from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/stay-cover/main.cpp').read_text();h=Path('solutions/perforated-fixed/perforate.hpp').read_text()
h=h.replace('static inline int overlap_samples=16;', 'static inline int overlap_samples=8;')
h=h.replace('static inline bool freeze_heads=false, head_candidates=true;', 'static inline bool freeze_heads=true, head_candidates=true;')
h=h.replace('std::array<double,26>', 'std::array<double,65>').replace('std::array<double,25>', 'std::array<double,64>').replace('>,25>', '>,64>').replace('>,26>', '>,65>')
h=h.replace('std::array<unsigned,26> used{};', 'std::array<u64,65> used{};').replace('(1U<<c)', '(1ULL<<c)')
h=h.replace('    int trials=0, accepted=0;', '    int trials=0, accepted=0;\n    double deadline=1e9;')
h=h.replace('''            for(auto[k,c]:candidates){
                trials++;''','''            for(auto[k,c]:candidates){
                if((trials&7)==0&&elapsed_sec()>=deadline)return;
                trials++;''')
a=h.index('        s.adaptive_initialized=false;s.init_adaptive();',h.index('    void install()'))
b=h.index('\n    }',a)
h=h[:a]+h[b:]
s=s.replace('\n}  // namespace\n\nint main()', '\n'+h+'\n}  // namespace\n\nint main()',1)
needle='''    solver.init_adaptive();
    if (M == Interleave::GM && comp.complete) {'''
assert needle in s
replacement='''    // Sacrifice a few printed handles when that makes a common donor
    // repair several other products more efficiently. Its own handle stays.
    const double perforation_start=elapsed_sec();
    Perforation perforation(solver);
    perforation.deadline=1.49;
    perforation.run(.5,1,false);
    perforation.install();
    papers=solver.paper;
    std::cerr << "perforation_holes = " << perforation.holes()
              << "\\nperforation_trials = " << perforation.trials
              << "\\nperforation_accepts = " << perforation.accepted
              << "\\nperforation_sec = " << elapsed_sec()-perforation_start
              << "\\nperforation_end_sec = " << elapsed_sec() << '\\n';
    solver.init_adaptive();
    if (M == Interleave::GM && comp.complete) {'''
s=s.replace(needle,replacement)
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''# 先頭候補の商品紙に補助用の穴を追加する\n\n改良元: solutions/stay-cover。穴の設計は solutions/perforated-fixed の8標本版。\n\n通常の共有・列の設計後、各列の白黒について先頭になりやすい紙を1枚ずつ選ぶ。その紙の自分の取り出し窓より浅い印刷に、追加の穴を開ける。誤色が消えることで、他の商品の複数の穴をまとめて覆いやすくする。自分の商品に増える穴の費用も数える。\n\n各商品の先頭色を固定乱数で8標本作り、重ならない穴埋めの区間DPで利益を測る。紙ごとの独立利益で事前選別し、区間DPの利益に係数0.5を掛けて追加・復元を1巡回する。評価用の先頭候補は固定するが、実際の操作では候補を制限しない。\n\n元の探索時間配分は保ち、穴追加は倍率込み経過1.49秒で打ち切る。補助表の上限1.55秒、注文処理の軽量化開始1.80秒も元と同じ。全時計はCLOCK_SCALE倍。main.cpp単独で完結し、表の大きさはハンドル数が増える場合にも対応する。\n\n追加のstderr指標: perforation_holesは追加穴数、perforation_trialsは試した1穴変更数、perforation_acceptsは受理数、perforation_secとperforation_end_secは穴追加の所要時間と終了時刻。\n''')
