from pathlib import Path
here=Path(__file__).resolve().parent
base=here.parents[1]/'solutions/esw-slim/main.cpp'
s=base.read_text()
title='Final generic-layer optimization: potential measurement'
s=s.replace('//   Helper tables: dedicated papers inside the generic layer (Interleave)',
            '//   '+title+'\n//   Helper tables: dedicated papers inside the generic layer (Interleave)',1)
pos=s.index('// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====')
s=s[:pos]+(here/'measurement.inc').read_text()+s[pos:]
needle='    // Restore the cap bit only for the physical papers and online targets.'
pos=s.index(needle)
s=s[:pos]+'''    const double d1_start = elapsed_sec();
    if (M == 6 && G == 38) {
        FinalGenericProbe probe(*des, comp);
        probe.run();
        if (env_int("ARGON_D1_APPLY")) probe.install(*des, comp, A, permutation);
    }
    std::cerr << "d1_sec = " << elapsed_sec() - d1_start << '\\n';
'''+s[pos:]
(here/'main.cpp').write_text(s)
