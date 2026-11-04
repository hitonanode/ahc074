from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-fixed/perforate.hpp').read_text()
s=s.replace('static inline int overlap_samples=16;', 'static inline int overlap_samples=8;')
s=s.replace('static inline bool freeze_heads=false, head_candidates=true;', 'static inline bool freeze_heads=true, head_candidates=true;')
batch=Path('solutions/perforated-batch/perforate.hpp').read_text()
a=batch.index('    void run(double weight,');b=batch.index('    int holes()',a)
body=batch[a:b].replace('void run(double weight,int passes,bool only_heads)', 'void run_targeted(double weight,int passes,int max_holes)')
a=body.index('            for(int k=7;');b=body.index('            std::shuffle',a)
body=body[:a]+'''            for(int k=7;k<K;k++){
                int c=columns[k],b=colors[k]>>c&1;
                if(k!=fixed_heads[c][b])continue;
                // Erase precisely the wrong printed windows that prevent
                // this donor from covering one recipient above a level.
                // This crosses barriers that a one-hole descent cannot cross.
                for(int u=0;u<P;u++){
                    if(s.ded[u]==k)continue;
                    u64 wrong=(colors[k]^target[u])&opacity[k]&~opacity[s.ded[u]];
                    if(wrong>>c&1)continue;
                    for(int lo=0;lo<c;lo++){
                        u64 remove=wrong&~low_bits(lo)&low_bits(c);
                        int size=__builtin_popcountll(remove);
                        if(size>=2&&size<=max_holes)candidates.push_back({k,remove});
                    }
                }
            }
            std::sort(candidates.begin(),candidates.end());
            candidates.erase(std::unique(candidates.begin(),candidates.end()),candidates.end());
'''+body[b:]
body=body.replace('trials++;u64 removed=opacity[k]&bit;', 'bit&=opacity[k];if(__builtin_popcountll(bit)<2)continue;trials++;u64 removed=opacity[k]&bit;')
body=body.replace('assert(std::abs(next-full_profit())<1e-7);','if(viable)assert(std::abs(next-full_profit())<1e-7);')
s=s.replace('    int holes()',body+'    int holes()')
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-fixed/probe.cpp').read_text()
a=s.index('Perforation::overlap_samples=');b=s.index('  double model=',a)
s=s[:a]+'''Perforation::overlap_samples=8;Perforation::screen_weight=1;Perforation design(s);double original=design.hole_cost-design.profit;
  if(setting==1)design.run(.5,1,false);
  else if(setting){
   double weight=setting==4?.35:.5;
   if(setting==5)design.run(weight,1,false);
   design.run_targeted(weight,1,setting==2?2:3);
   design.run(weight,1,false);
  }
'''+s[b:]
(p/'probe.cpp').write_text(s)
s=Path('solutions/perforated-fixed/run.py').read_text().replace('ahc074-perforated-fixed','ahc074-perforated-target').replace('range(24,56)','range(88,120)')
(p/'run.py').write_text(s)
