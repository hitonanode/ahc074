"""対ごとのハンドル差のばらつきを足す追加実験。"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'variants.cpp').read_text()
needle='    const double proxy_sd ='
pos=s.index(needle)
s=s[:pos]+'''    const double proxy_pair_sd = std::getenv("PROXY_PAIR_SD") ? std::atof(std::getenv("PROXY_PAIR_SD")) : 0.0;
'''+s[pos:]
needle='        return double(total) / (need * 3600) + (need - matched) * 10.0 - bonus;'
new=r'''
        if (proxy_pair_sd && matched) {
            int sum=0,sq=0;
            for (int p:candidate_selected) {
                const int h=__builtin_popcountll(pairs.diff[p]&handle_mask);
                sum+=h;sq+=h*h;
            }
            const double mean=double(sum)/matched;
            bonus+=proxy_pair_sd*std::sqrt(std::max(0.,double(sq)/matched-mean*mean));
        }
'''
assert s.count(needle)==1;s=s.replace(needle,new+needle)
(HERE/'pairvar.cpp').write_text(s)
