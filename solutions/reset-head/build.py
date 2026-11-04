from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'anchor-match/main.cpp').read_text()
helper=(p.parent/'anchor-match/matching.hpp').read_text().split('MatchStats rematch(')[0]
head=(p.parent/'head-prob/prob.hpp').read_text()
head=head.replace('double strength,bool dynamic,bool derivative){','double strength,bool dynamic,bool derivative,double deadline=1e100){')
head=head.replace('for(int it=0;it<iterations;it++){','''double previous_seconds=0;
 for(int it=0;it<iterations;it++){
  if(elapsed_sec()+previous_seconds>deadline)break;
  double iteration_start=elapsed_sec();''')
head=head.replace('stats.iterations++;','stats.iterations++;previous_seconds=elapsed_sec()-iteration_start;')
a=s.index('// Global reassignment of mobile products, with the filler-head objective.')
b=s.index('\n#endif\nstruct Paper {',a)
s=s[:a]+'// Global reassignment with updated head-color probabilities.\n'+helper+'\n'+head+s[b:]
s=s.replace('rematch_head(*des, 4, 1.0, 1.445)','rematch_probability(*des, 4, 1.0, 2.0, true, true, 1.445)')
s=s.replace('double n=hn[c][0]+hn[c][1];double p=n?hn[c][1]/n:.5;', 'double x=hn[c][0],y=hn[c][1],t=2.0*nt[c],n=x+y+t;double p=n?(y+t*(y>x))/n:.5;')
(p/'main.cpp').write_text(s)
