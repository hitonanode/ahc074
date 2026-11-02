"""校正した三項目的の候補を、as6-imb0gb から作る。"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
root=HERE.parent.parent
s=(root/'solutions/as6-imb0gb/main.cpp').read_text()
v=(HERE/'variants.cpp').read_text()
a=v.index('    const double proxy_bias =')
b=v.index('    // Only `valid[0..nvalid)`',a)
pre=v[a:b]
pre=pre.replace('const double proxy_bias = std::getenv("PROXY_BIAS") ? std::atof(std::getenv("PROXY_BIAS")) : 0.0;',
                'constexpr double proxy_bias = 0.001;')
pre=pre.replace('const double proxy_sd = std::getenv("PROXY_SD") ? std::atof(std::getenv("PROXY_SD")) : 0.0;',
                'constexpr double proxy_sd = 0.07;')
needle='    // Only `valid[0..nvalid)`'
s=s.replace(needle,pre+needle)
a=v.index('        double bonus=0;')
b=v.index('    };',a)
body=v[a:b]
needle='        return double(total) / (need * 3600) + (need - matched) * 10.0;'
assert s.count(needle)==1
s=s.replace(needle,body.rstrip())
s=s.replace('"gobj_before = "','"gproxy_before = "').replace('"\\ngobj_after = "','"\\ngproxy_after = "')
s='''// astra-gproxy: as6-imb0gb with an assignment objective predicting the final design cost.
// Keep the pair-selection keys, and subtract 0.001 * mean((black_count - 128)^2)
// over the 25 handles and 0.07 * stddev(conflicting_pair_count) over those handles.
// Counts use only public target patterns and the greedy selected 71 pairs; request handling,
// design annealing, the clocks and all random seeds are unchanged (README.md).
'''+s
(HERE/'main.cpp').write_text(s)
