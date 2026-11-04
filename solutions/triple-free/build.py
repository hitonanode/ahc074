from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'triple-latent/dp_search.cpp').read_text()
ctor=s[s.index('  std::ifstream in(path)'):s.index('  for(auto&x:groups){')]
(p/'ctor.inc').write_text(ctor)
