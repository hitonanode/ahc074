#!/usr/bin/env python3
"""固定回数の検査用コピーを作る。受理状態と返却値を全対再計算する。"""
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('target');a=p.parse_args()
h=Path(__file__).resolve().parent
s=(h/(a.target+'.cpp')).read_text()
s=s.replace('    long long screen_rejected =','    long long verify_intermediate=0, verify_returned=0;\n    long long screen_rejected =',1)
needle='''        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);'''
code='''
        if ((accepted&127)==0) {
            for (int p=0;p<np;++p) {
                uint32_t r; int rel;
                pair_state(pairs.au[p],pairs.diff[p],r,rel);
                assert(r==pairs.dir[p]); assert(rel==pairs.rel[p]);
                ++verify_intermediate;
            }
            int old_nvalid=nvalid;
            nvalid=0;
            for (int p=0;p<np;++p) if (pairs.rel[p]) valid[nvalid++]=p;
            const double exact=matching_cost(pairs.rel.data(),handles_after(mv));
            assert(std::abs(exact-memo_value[move_key])<1e-9);
            nvalid=old_nvalid;
        }
'''
assert needle in s;s=s.replace(needle,needle+code,1)
needle='    stats.gobj_after = cur;'
code='''    {
        u64 generic=0;
        for (u64 windows:mask) { assert(windows); assert(!(generic&windows)); generic|=windows; }
        assert(__builtin_popcountll(generic)==g); assert(!(generic&kCapBit));
        u64 seen=0;
        for (int j=0;j<64;++j) {
            assert(!(seen>>order[j]&1)); seen|=1ULL<<order[j];
            assert(bool(generic>>order[j]&1)==(j<g));
        }
        assert(order[63]==63);
        nvalid=0;
        for (int p=0;p<np;++p) {
            pair_state(pairs.au[p],pairs.diff[p],ndir[p],nrel[p]);
            if (nrel[p]) valid[nvalid++]=p;
            ++verify_returned;
        }
        const double exact=matching_cost(nrel.data(),kActiveWindows&~generic);
        assert(std::abs(exact-cur)<1e-9);
    }
    std::cerr << "verify_intermediate = " << verify_intermediate << "\\nverify_returned = " << verify_returned << '\\n';
'''
assert needle in s;s=s.replace(needle,code+needle,1)
if 'auto prepare_double =' in s:
 needle='                    if (lost<kRejectLoss) choices[count++]=b | (d<<6) | (cb<<12) | (cd<<13);'
 code='''                    if ((double_rows&127)==0) {
                        const u64 oldma=mask[ea], oldpol=pol;
                        mask[ea]=rest|(1ULL<<b)|(1ULL<<d);
                        pol=(pol&~((1ULL<<b)|(1ULL<<d)))|(u64(cb)<<b)|(u64(cd)<<d);
                        int exact=0;
                        for (int p:selected) {
                            uint32_t r; int rel;
                            pair_state(pairs.au[p],pairs.diff[p],r,rel);
                            exact+=rel==0;
                        }
                        assert(exact==lost); ++verify_double;
                        mask[ea]=oldma; pol=oldpol;
                    }
'''
 assert needle in s;s=s.replace(needle,code+needle,1)
 s=s.replace('long long verify_intermediate=0,','long long verify_double=0, verify_intermediate=0,',1)
 s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "verify_double = " << verify_double << \'\\n\';\n    stats.gobj_after = cur;',1)
(h/'verify-check.cpp').write_text(s)
