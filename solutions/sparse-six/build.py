from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/sparse-control/main.cpp').read_text()
s=s.replace('static int sparse_map_mode=0;', 'static int sparse_map_mode=1;')
s=s.replace('''        comp.rebuild();
        des = std::make_unique<Design>(A, M, G);''','''        comp.rebuild();
        // Missing comparisons change which sheets are visible. Price pairs
        // with that graph before optimizing their sharing and columns.
        if(!comp.complete)comp.build_tables();
        des = std::make_unique<Design>(A, M, G);''',1)
s=s.replace('''        auto estimate = [&](u64 a, u64 b) {
            const auto reach = comp.closure(a, a ^ b);''','''        auto estimate = [&](u64 a, u64 b) {
            if(!comp.complete)return .5*(comp.mean_moves(a,a^b)+comp.mean_moves(b,a^b));
            const auto reach = comp.closure(a, a ^ b);''',1)
s=s.replace('if (M == Interleave::GM && comp.complete) {','if (M == Interleave::GM) {')
needle='''    std::cerr << "map_iters = " << map_total << "\\nmap_end_sec = " << elapsed_sec() << '\\n';'''
assert needle in s
s=s.replace(needle,'''    std::array<std::array<bool,6>,6> used_edges{};int distinct_edges=0;
    for(auto[a,b]:comp.edge)if(!used_edges[a][b])used_edges[a][b]=used_edges[b][a]=true,distinct_edges++;
    std::cerr << "generic_edges = " << distinct_edges << '\\n';
'''+needle)
(p/'main.cpp').write_text(s)
