from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-fixed/perforate.hpp').read_text()
s=s.replace('static inline int overlap_samples=16;', 'static inline int overlap_samples=8, sample_mode=0;\n    static inline std::vector<u64> empirical_colors;')
s=s.replace('static inline bool freeze_heads=false, head_candidates=true;', 'static inline bool freeze_heads=true, head_candidates=true;')
old='''        for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;'''
assert old in s
s=s.replace(old,'''        if(sample_mode==0){
            for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;
        }else if(sample_mode==1){
            // One request sets all its holes together. Independent return
            // events reset their own columns at twice the product frequency.
            // This keeps the marginal reset model and adds cross-column dependence.
            u64 colors=0,majority=0;for(int c=0;c<H;c++)if(counts[c][1]>counts[c][0])majority|=1ULL<<c;
            int stored=0;
            for(int t=0;stored<int(samples.size());t++){
                int u=random()%P;u64 holes=low_bits(H)&~opacity[s.ded[u]];
                colors=(colors&~holes)|(target[u]&holes);
                for(int r=0;r<2;r++){int c=columns[s.ded[random()%P]];u64 bit=1ULL<<c;colors=(colors&~bit)|(majority&bit);}
                if(t>=4096&&(t&7)==0)samples[stored++]=colors;
            }
        }else{
            assert(!empirical_colors.empty());
            for(auto&bits:samples)bits=empirical_colors[random()%empirical_colors.size()];
        }''')
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-fixed/probe.cpp').read_text()
s=s.replace(' int sequences=argc>3?', '''
 Solver observed=*base;std::mt19937_64 training(718000003);int previous=training()%P;
 double sampling_start=elapsed_sec();std::vector<u64> observed_colors;
 for(int t=0;t<4352;t++){
  int u=training()%(P-1);if(u>=previous)u++;previous=u;
  observed.process(u);assert(observed.display()==observed.A[u]);
  if(t<256||(t&15))continue;
  u64 colors=0;
  for(int c=0;c<observed.H;c++){
   int k=observed.column_top(c);
   if(k<0&&observed.top_d>=0&&observed.col_of[observed.top_d]==c)k=observed.top_d;
   if(k<0)for(auto f:observed.fillers)if(observed.col_of[f.paper]==c){k=f.paper;break;}
   assert(k>=0);if(observed.h_blk[k]>>c&1)colors|=1ULL<<c;
  }
  observed_colors.push_back(colors);
 }
 double sampling_seconds=elapsed_sec()-sampling_start;
 Perforation::empirical_colors=observed_colors;
 std::cerr<<"sampling_sec = "<<sampling_seconds<<'\\n';
 int sequences=argc>3?''')
a=s.index('Perforation::overlap_samples=');b=s.index('  double model=',a)
s=s[:a]+'''Perforation::overlap_samples=(setting==3||setting==5)?32:8;Perforation::sample_mode=setting<=1?0:setting<=3?1:2;Perforation::screen_weight=1;Perforation design(s);double original=design.hole_cost-design.profit;
  if(setting)design.run(.5,1,false);
'''+s[b:]
(p/'probe.cpp').write_text(s)
s=Path('solutions/perforated-fixed/run.py').read_text().replace('ahc074-perforated-fixed','ahc074-perforated-markov').replace('range(24,56)','range(120,152)')
(p/'run.py').write_text(s)
