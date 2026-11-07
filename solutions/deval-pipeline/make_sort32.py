from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
for name,base in [('deval-sort32','deval-ordered8'),('deval-sort32-msd','deval-sort-msd9')]:
 b=(R/'solutions'/base/'main.cpp').read_text()
 start=b.index('    std::vector<u64> keyed(np), tmp(np), sorted(np);')
 end=b.index('    // ==== Window assignment: candidate screens and tables ====',start)
 t=b[start:end].replace('std::vector<u64> keyed(np), tmp(np), sorted(np);','std::vector<uint32_t> keyed(np), tmp(np), sorted(np);',1)
 t=t.replace('keyed[i] = u64(key) << 32 | pair_tail[p];','keyed[i] = uint32_t(key) << 15 | uint32_t(p);',1)
 t=t.replace('(keyed[i] >> 32)', '(keyed[i] >> 15)').replace('tmp[i] >> 40','tmp[i] >> 23').replace('keyed[i]>>41','keyed[i]>>24')
 t=t.replace('''            const u64 x = sorted[i];
            const unsigned u = unsigned(x >> 8) & 255, v = unsigned(x) & 255;''','''            const uint32_t x = sorted[i], p=x&32767;
            const uint32_t tail=pair_tail[p];
            const unsigned u = (tail >> 8) & 255, v = tail & 255;''',1)
 t=t.replace('out[matched] = int(x >> 16) & 0xffff;','out[matched] = p;',1).replace('(long long)(x >> 32)','(long long)(x >> 15)',1)
 s=b[:start]+t+b[end:]
 s=s.replace('''    // a sort entry packs key << 32 | pair << 16 | u << 8 | v (pair_tail[p]: the low half), so
    // the ascending order of the entries is stable by key (ties in the order
    // of the pairs, as valid[] lists them) and the greedy reads the two targets from the entry.''','''    // A 17-bit cost and a 15-bit pair index fit one uint32_t (at most 32640
    // unordered pairs). Ascending integer order preserves all original ties;
    // the two targets are fetched from pair_tail after sorting.''',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/{base}`。\n\n窓マッチングの整列キーを32 bitへ縮める。17 bitの整数費用と15 bitのペア番号を保持し、目標2つの番号はペア表から読む。ペアは最大32640個なので、同値順を含め完全に同じ整列になる。目的関数・乱数列・探索回数を保つ。\n')
 print(name,len(s.encode()))
