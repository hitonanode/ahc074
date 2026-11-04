from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'reset-majority/main.cpp').read_text()
helper=(p/'matching.hpp').read_text().split('MatchStats rematch(')[0]
head=(p/'head.hpp').read_text()
head=head.replace('int iterations,double weight){','int iterations,double weight,double deadline=1e100){')
head=head.replace('for(int it=0;it<iterations;it++){', '''double previous_seconds=0;
 for(int it=0;it<iterations;it++){
  if(elapsed_sec()+previous_seconds>deadline)break;
  double iteration_start=elapsed_sec();''')
head=head.replace('stats.iterations++;','stats.iterations++;previous_seconds=elapsed_sec()-iteration_start;')
s=s.replace('\nstruct Paper {', '\n#ifndef ANCHOR_RESEARCH\n// Global reassignment of mobile products, with the filler-head objective.\n'+helper+'\n'+head+'\n#endif\nstruct Paper {',1)
needle='    // Restore the cap bit only for the physical papers and online targets.'
code='''    const auto match = rematch_head(*des, 4, 1.0, 1.445);
    std::cerr << "match_iterations = " << match.iterations << "\\nmatch_cycles = " << match.accepted_cycles
              << "\\nmatch_changed = " << match.changed << "\\nmatch_decrease = " << match.decrease
              << "\\nmatch_sec = " << match.seconds << "\\nmatch_end_sec = " << elapsed_sec() << '\\n';

'''
s=s.replace(needle,'#ifndef ANCHOR_RESEARCH\n'+code+'#endif\n'+needle)
(p/'main.cpp').write_text(s)
