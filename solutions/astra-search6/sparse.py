"""矛盾方向の組で分類し、変化しうる商品対だけを評価する。"""
def sparse(t, mode):
    needle='    auto propose = [&](Move& mv)'
    k=t.index(needle)
    code=r'''    // A relation with opposed arcs outside the edited groups cannot become a DAG.
    // Bucket by the at-most-two groups containing opposed arcs. This is an exact filter;
    // longer cycles and the exact costs are still checked by WindowRelations::cost.
    std::array<std::vector<int>, 241> conflict_buckets;
    std::array<std::vector<int>, 225> active_pairs;
    std::array<unsigned, 225> active_epoch{};
    unsigned bucket_epoch = 0;
    std::vector<int> merged_pairs;
    long long sparse_pairs = 0, sparse_evals = 0;
    bool sparse_pending = false;
    auto evaluate_sparse = [&](int ea, int eb) __attribute__((target("avx2,popcnt"))) {
        const int lo = std::min(ea,eb), hi = std::max(ea,eb), key = 15*lo+hi;
        if (bucket_epoch != epoch) {
            for (auto& b : conflict_buckets) b.clear();
            for (int p = 0; p < np; ++p) {
                const uint32_t r = pairs.dir[p], bad = r & (r >> 16);
                int b = 0;
                if (bad) {
                    const int count = __builtin_popcount(bad);
                    if (count > 2) continue;
                    const int a = __builtin_ctz(bad);
                    b = count == 1 ? 1+a : 16+15*a+__builtin_ctz(bad & (bad-1));
                }
                conflict_buckets[b].push_back(p);
            }
            bucket_epoch = epoch;
        }
        auto& active = active_pairs[key];
        if (active_epoch[key] != epoch) {
            active = conflict_buckets[0];
            const int buckets[3] = {1+lo,1+hi,16+key};
            const int count = lo == hi ? 1 : 3;
            for (int j = 0; j < count; ++j) {
                const auto& extra = conflict_buckets[buckets[j]];
                merged_pairs.resize(active.size()+extra.size());
                std::merge(active.begin(),active.end(),extra.begin(),extra.end(),merged_pairs.begin());
                active.swap(merged_pairs);
            }
            active_epoch[key] = epoch;
        }
        const uint32_t keep = ~uint32_t(fwd[ea] | rev[ea] | fwd[eb] | rev[eb]);
        const u64 ma = mask[ea], mb = mask[eb];
        int nv = 0;
        ++sparse_evals; sparse_pairs += active.size();
        for (int p : active) {
            const u64 z = pairs.au[p] ^ pol;
            const u64 qa = pairs.diff[p] & ma, qb = pairs.diff[p] & mb;
            uint32_t r = pairs.dir[p] & keep;
            if (qa & ~z) r |= fwd[ea];
            if (qa & z) r |= rev[ea];
            if (qb & ~z) r |= fwd[eb];
            if (qb & z) r |= rev[eb];
            const int rel = r == pairs.dir[p] ? pairs.rel[p] : relations.cost(r);
            if (rel) { nrel[p] = rel; valid[nv++] = p; }
        }
        sparse_pending = true;
        return nv;
    };
'''
    if mode==2:
        # Store contiguous pair data once per group combination; evaluate four 64-bit masks at once.
        code=code.replace('    std::array<unsigned, 225> active_epoch{};', '''    struct SparseData { std::vector<u64> diff, au, dir; std::vector<int> rel; };
    std::array<SparseData, 225> active_data;
    std::array<unsigned, 225> active_epoch{};''')
        code=code.replace('            active_epoch[key] = epoch;', '''            auto& data = active_data[key];
            const int padded = (int(active.size())+3)&~3;
            data.diff.assign(padded,0); data.au.assign(padded,0);
            data.dir.assign(padded,0); data.rel.assign(padded,0);
            for (int i = 0; i < int(active.size()); ++i) {
                const int p = active[i];
                data.diff[i] = pairs.diff[p]; data.au[i] = pairs.au[p];
                data.dir[i] = pairs.dir[p]; data.rel[i] = pairs.rel[p];
            }
            active_epoch[key] = epoch;''')
        a=code.index('        for (int p : active) {');b=code.index('        sparse_pending = true;',a)
        code=code[:a]+r'''        const auto& data = active_data[key];
        const __m256i zero = _mm256_setzero_si256(), vpol = set1_u64(pol), vkeep = set1_u64(keep);
        const __m256i va = set1_u64(ma), vb = set1_u64(mb);
        const __m256i af = set1_u64(fwd[ea]), ar = set1_u64(rev[ea]);
        const __m256i bf = set1_u64(fwd[eb]), br = set1_u64(rev[eb]);
        alignas(32) u64 result[4];
        for (int i = 0; i < int(active.size()); i += 4) {
            const __m256i d = _mm256_loadu_si256((const __m256i*)(data.diff.data()+i));
            const __m256i z = _mm256_xor_si256(_mm256_loadu_si256((const __m256i*)(data.au.data()+i)),vpol);
            const __m256i qa = _mm256_and_si256(d,va), qb = _mm256_and_si256(d,vb);
            __m256i r = _mm256_and_si256(_mm256_loadu_si256((const __m256i*)(data.dir.data()+i)),vkeep);
            r = _mm256_or_si256(r,_mm256_andnot_si256(_mm256_cmpeq_epi64(_mm256_andnot_si256(z,qa),zero),af));
            r = _mm256_or_si256(r,_mm256_andnot_si256(_mm256_cmpeq_epi64(_mm256_and_si256(z,qa),zero),ar));
            r = _mm256_or_si256(r,_mm256_andnot_si256(_mm256_cmpeq_epi64(_mm256_andnot_si256(z,qb),zero),bf));
            r = _mm256_or_si256(r,_mm256_andnot_si256(_mm256_cmpeq_epi64(_mm256_and_si256(z,qb),zero),br));
            _mm256_store_si256((__m256i*)result,r);
            for (int j = 0; j < 4 && i+j < int(active.size()); ++j) {
                const uint32_t next = uint32_t(result[j]);
                const int rel = next == data.dir[i+j] ? data.rel[i+j] : relations.cost(next);
                if (rel) { const int p = active[i+j]; nrel[p] = rel; valid[nv++] = p; }
            }
        }
'''+code[b:]
    if mode==3:
        # Remove all longer cycles once per active set, as the erased relation is invariant here.
        code=code.replace('            active_epoch[key] = epoch;', '''            const uint32_t keep = ~uint32_t(fwd[ea] | rev[ea] | fwd[eb] | rev[eb]);
            int count_valid = 0;
            for (int p : active) if (relations.cost(pairs.dir[p] & keep)) active[count_valid++] = p;
            active.resize(count_valid);
            active_epoch[key] = epoch;''')
    t=t[:k]+code+t[k:]
    a=t.index('        // on all the pairs (those that do not differ at a or b come out unchanged)');b=t.index('        return true;',a)
    t=t[:a]+'''        nvalid = evaluate_sparse(ea,eb);
'''+t[b:]
    t=t.replace('    auto apply_move = [&](const Move& mv) {\n        if (memo_hit) {','    auto apply_move = [&](const Move& mv) {\n        if (memo_hit || sparse_pending) {')
    t=t.replace('            matching_cost(nrel.data(), handles_after(mv));', '            if (memo_hit) matching_cost(nrel.data(), handles_after(mv));\n            sparse_pending = false;',1)
    t=t.replace('    stats.gobj_after = cur;', '''    std::cerr << "sparse_pairs = " << sparse_pairs << "\\nsparse_evals = " << sparse_evals << '\\n';
    stats.gobj_after = cur;''',1)
    return t
