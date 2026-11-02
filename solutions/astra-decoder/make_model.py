from pathlib import Path
root=Path(__file__).resolve().parent
s=(root.parent/'as6-cap38p0/main.cpp').read_text()
s=s.replace('constexpr double kHelperGiveUp = 1.55;', 'const double kHelperGiveUp = env_int("MAP_ITERS") ? 1e9 : 1.55;')
a='''        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; }))'''
b='''        // Research-only relaxation: the additional pairs are not necessarily displayable.
        const int cfree = env_int("COMPAT_FREE");
        const double cgx = env_int("COMPAT_GX") / 100.0;
        auto compatible2 = [&](u64 a, u64 b) {
            return comp.compatible(a, b) || (cfree && __builtin_popcountll(a ^ b) <= cfree);
        };
        auto estimate2 = [&](u64 a, u64 b) { return comp.compatible(a, b) ? estimate(a, b) : cgx; };
        if (des->initialize(compatible2, estimate2,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; }))'''
assert a in s;s=s.replace(a,b)
a='''    // Papers: six generic sheets, the cap, then the columns 0, 1, ... (colors alternate,'''
b='''    {
        int npairs = 0, incompat = 0, shallow = 0, gh = 0, fullhd = 0;
        double gcpair = 0;
        for (const auto& u : des->unit) if (u.b >= 0) {
            ++npairs;
            incompat += !comp.compatible(des->A[u.a], des->A[u.b]);
            shallow += __builtin_popcountll((des->hb[u.a] ^ des->hb[u.b]) & low_bits(u.c + 1));
            gh += __builtin_popcountll((des->A[u.a] ^ des->A[u.b]) & low_bits(G));
            fullhd += __builtin_popcountll(des->A[u.a] ^ des->A[u.b]);
            gcpair += des->gc(u);
        }
        std::cerr << "pairs_incompat = " << incompat << "\\npair_gc_mean = " << gcpair / (2 * npairs)
                  << "\\npair_shallow_hd = " << double(shallow) / npairs
                  << "\\npair_generic_hd = " << double(gh) / npairs
                  << "\\npair_full_hd = " << double(fullhd) / npairs << '\\n';
        if (env_int("DUMP_DESIGN")) {
            std::cout << "{\\"M\\":" << M << ",\\"G\\":" << G << ",\\"A\\":[";
            for (int i=0;i<P;++i) std::cout << (i ? "," : "") << des->A[i];
            std::cout << "],\\"edges\\":[";
            for(int j=0;j<G;++j) std::cout << (j?",":"") << '[' << comp.edge[j].first << ',' << comp.edge[j].second << ',' << comp.polarity[j] << ']';
            std::cout << "],\\"permutation\\":[";
            for(int j=0;j<64;++j) std::cout << (j?",":"") << permutation[j];
            std::cout << "],\\"handles\\":[";
            for(int j=0;j<des->H;++j) std::cout << (j?",":"") << des->handle[j];
            std::cout << "],\\"units\\":[";
            for(int j=0;j<des->U;++j) { const auto& u=des->unit[j]; std::cout << (j?",":"") << '[' << u.a << ',' << u.b << ',' << u.c << ']'; }
            std::cout << "]}\\n";
        }
        if (env_int("MODEL_ONLY")) return 0;
    }

'''+a
assert a in s;s=s.replace(a,b)
s=s.replace('if (t_req > kFastAfter) solver.fast_mode = true;', 'if (!env_int("MAP_ITERS") && t_req > kFastAfter) solver.fast_mode = true;')
(root/'model.cpp').write_text(s)
