"""as6-imb0gb を元に、割り当て乱数・状態の記録・固定回数模擬を足す。"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
src = (ROOT / "solutions/as6-imb0gb/main.cpp").read_text()
src = src.replace('XorShift rng{0x71eb2566be932e31ULL};', '''
    const auto map_seed = static_cast<u64>(env_int("MAP_SEED"));
    XorShift rng{0x71eb2566be932e31ULL ^ (map_seed * 0x9E3779B97F4A7C15ULL)};''')
src = src.replace('std::mt19937_64 rng(779879);', 'std::mt19937_64 rng(779879 ^ env_int("MAP_SEED"));')
src = src.replace('solver.hmask, kHelperGiveUp);', 'solver.hmask, anneal_iters > 0 ? 1e9 : kHelperGiveUp);')

dump = r'''
    // Research only: recompute the returned best state, without consuming random numbers.
    if (env_int("DUMP_MAP")) {
        hm = kActiveWindows;
        for (u64 q : mask) hm &= ~q;
        nvalid = 0;
        for (int p = 0; p < np; ++p) {
            pair_state(pairs.au[p], pairs.diff[p], pairs.dir[p], pairs.rel[p]);
            if (pairs.rel[p]) valid[nvalid++] = p;
        }
        matching_cost(pairs.rel.data(), hm);
        std::cout << "A";
        for (auto a : A) std::cout << ' ' << a;
        std::cout << "\nMASK";
        for (auto x : mask) std::cout << ' ' << x;
        std::cout << "\nPOL " << pol << "\nHM " << hm << "\nSELECT";
        for (int p : candidate_selected) std::cout << ' ' << pairs.u[p] << ' ' << pairs.v[p];
        std::cout << "\nVALID";
        for (int i = 0; i < nvalid; ++i) {
            const int p = valid[i];
            std::cout << ' ' << pairs.u[p] << ' ' << pairs.v[p] << ' ' << pairs.rel[p] - 1;
        }
        std::cout << '\n';
    }
'''
needle = '    stats.gobj_after = cur;'
assert src.count(needle) == 1
src = src.replace(needle, dump + needle)

dump_final = r'''
    if (env_int("DUMP_MAP")) {
        std::cout << "HANDLE";
        for (int h : des->handle) std::cout << ' ' << permutation[h];
        std::cout << "\nUNIT";
        for (auto u : des->unit) std::cout << ' ' << u.a << ' ' << u.b << ' ' << u.c;
        std::cout << '\n';
    }
    if (env_int("RESEARCH_ONLY")) return 0;
'''
needle = '    // Papers: six generic sheets, the cap, then the columns'
assert src.count(needle) == 1
src = src.replace(needle, dump_final + '\n' + needle)
(HERE / 'probe.cpp').write_text(src)
