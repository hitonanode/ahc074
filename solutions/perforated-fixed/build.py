from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-crossing/perforate.hpp').read_text()
s=s.replace('    static inline int overlap_samples=16;', '''    static inline int overlap_samples=16;
    static inline bool freeze_heads=false, head_candidates=true;
    std::vector<std::array<int,2>> fixed_heads;''')
s=s.replace('        rebuild();\n    }', '        rebuild();if(freeze_heads)fixed_heads=cache_heads;\n    }',1)
s=s.replace('''    double separate_profit()const{
        std::vector<std::array<double,2>> best(H);''','''    double separate_profit()const{
        if(!fixed_heads.empty()){
            double sum=0;for(int c=0;c<H;c++)for(int b=0;b<2;b++)sum+=probability[c][b]*utility[fixed_heads[c][b]];return sum;
        }
        std::vector<std::array<double,2>> best(H);''')
s=s.replace('''    std::vector<std::array<int,2>> choose_heads()const{
        std::vector''', '''    std::vector<std::array<int,2>> choose_heads()const{
        if(!fixed_heads.empty())return fixed_heads;
        std::vector''')
s=s.replace('''                if(only_heads&&frequency[k]!=max_frequency[c][b])continue;''','''                if(only_heads&&frequency[k]!=max_frequency[c][b])continue;
                if(!fixed_heads.empty()&&head_candidates&&k!=fixed_heads[c][b])continue;''')
# Full recalculation for validation must use the same fixed donor set.
a=s.index('        std::vector<std::array<int,2>> heads(H,std::array<int,2>{-1,-1});',s.index('double full_profit'))
b=s.index('        double sum=0;',a)
s=s[:a]+'        auto heads=choose_heads();\n'+s[b:]
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-crossing/probe.cpp').read_text().replace('setting<4','setting<6')
s=s.replace('Perforation::overlap_samples=16;', 'Perforation::overlap_samples=setting==3?8:setting==4?4:16;Perforation::freeze_heads=setting>=2;Perforation::head_candidates=setting!=5;')
s=s.replace('Perforation::crossing_cache=setting>=2;Perforation::skip_equal=setting==3;', 'Perforation::crossing_cache=true;Perforation::skip_equal=true;')
(p/'probe.cpp').write_text(s)
s=Path('solutions/perforated-crossing/run.py').read_text().replace('ahc074-perforated-crossing','ahc074-perforated-fixed').replace('range(1,4)','range(1,6)');(p/'run.py').write_text(s)
(p/'README.md').write_text('''# 穴追加の評価で供給紙を固定する\n\n改良元: solutions/perforated-crossing。\n\n各列の白黒の先頭候補を、追加穴を開ける前の頻度と穴埋め利益で1枚ずつ選び、その集合を固定して穴を設計する。候補となる紙が途中で入れ替わると、多数の列の区間DPを計算し直す必要があるため、その計算を省く。固定は設計の近似模型だけに用い、実際の注文での紙の順序や選択は制限しない。\n\n穴追加を選ばれた紙だけに限る条件と、全紙を試す条件を比較。先頭色の標本は4/8/16個、利益係数0.5。差分計算を全再計算で照合し、独立した模擬注文で品質を見る。\n\n研究用。隠された注文列は読まず、CLOCK_SCALEを適用する。main.cppは制御の基準post-repairのコピーで、新しい設計はprobe.cppで調べる。\n''')
