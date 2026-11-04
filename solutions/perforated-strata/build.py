from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-fixed/perforate.hpp').read_text()
s=s.replace('static inline int overlap_samples=16;', 'static inline int overlap_samples=8, sample_mode=0;')
s=s.replace('static inline bool freeze_heads=false, head_candidates=true;', 'static inline bool freeze_heads=true, head_candidates=true;')
needle='''        for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;'''
assert needle in s
s=s.replace(needle,'''        if(sample_mode==0){
            for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;
        }else for(int u=0;u<P;u++)for(int c=0;c<H;c++){
            if(sample_mode==1){
                // Each marginal uses every stratum once, while columns have
                // independent permutations. This avoids accidental color bias.
                std::vector<int> permutation(overlap_samples);std::iota(permutation.begin(),permutation.end(),0);std::shuffle(permutation.begin(),permutation.end(),random);
                for(int t=0;t<overlap_samples;t++)if((permutation[t]+(random()>>11)*0x1.0p-53)/overlap_samples<probability[c][1])samples[u*overlap_samples+t]|=1ULL<<c;
            }else{
                for(int t=0;t<overlap_samples/2;t++){
                    double v=(random()>>11)*0x1.0p-53;
                    if(v<probability[c][1])samples[u*overlap_samples+2*t]|=1ULL<<c;
                    if(1-v<probability[c][1])samples[u*overlap_samples+2*t+1]|=1ULL<<c;
                }
            }
        }''')
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-fixed/probe.cpp').read_text().replace('setting<6','setting<7')
a=s.index('Perforation::overlap_samples=');b=s.index('  double model=',a)
s=s[:a]+'''Perforation::overlap_samples=setting==6?16:8;Perforation::sample_mode=setting<=1?0:setting==3?2:1;Perforation::screen_weight=1;Perforation design(s);double original=design.hole_cost-design.profit;
  if(setting)design.run(setting==4?.4:setting==5?.6:.5,1,false);
'''+s[b:]
(p/'probe.cpp').write_text(s)
s=Path('solutions/perforated-fixed/run.py').read_text().replace('range(24,56)','range(56,88)').replace('ahc074-perforated-fixed','ahc074-perforated-strata').replace('range(1,6)','range(1,7)');(p/'run.py').write_text(s)
(p/'README.md').write_text('''# 穴設計の色標本を層化して偏りを抑える\n\n改良元: solutions/perforated-fixed。制御は solutions/stay-cover。\n\n各商品の各窓について先頭色を独立に8回引くと、少ない標本で色の割合が大きく偏る。各窓で確率区間を8分割し、それぞれから1標本ずつ取って独立に並べ替える層化抽出と、乱数vと1−vを組にする反対変数法を調べる。先頭候補の固定と区間DPの目的は同じ。\n\n層化8標本の利益係数0.4/0.5/0.6、16標本の係数0.5も比較する。選別用の乱数と検査用の模擬注文は独立。以前の選別とは異なるseed56〜87を使う。\n\n研究用。main.cpp単独は制御の基準。隠された注文は使わず、CLOCK_SCALEを適用する。\n''')
