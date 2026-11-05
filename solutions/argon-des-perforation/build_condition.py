"""Condition owner-target differences on both colors of the changed handle."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
for source,name in [('esw-slim','argon-des-perf-condition'),('argon-des-perforation','argon-des-perf-condwide')]:
    out=root/name;assert not out.exists();out.mkdir()
    s=(root/source/'main.cpp').read_text();wide=source!='esw-slim'
    start=s.index('struct Perforation {');end=s.index('// ==== Design state:',start);p=s[start:end]
    p=p.replace('    int trials = 0, accepted = 0;', '''    int trials = 0, accepted = 0;
    double last_owner_raw = 0, last_owner_corrected = 0;
    double accepted_owner_raw = 0, accepted_owner_corrected = 0, accepted_donor = 0;
''')
    t=p.index('    double total_profit(int k) {');te=p.index('    // Everything from the current opacity',t)
    fn=p[t:te]
    fn=fn.replace('''        const int c = columns[k];''','''        const int c = columns[k];
        const u64 changed = opacity[k] ^ cache_opacity[k];
        assert(__builtin_popcountll(changed) == 1);
        const int changed_handle = __builtin_ctzll(changed);
        last_owner_raw = last_owner_corrected = 0;''')
    call='make_edges(u, samples[i], i)'if wide else 'make_edges(u, samples[i])'
    flipped='make_edges(u, samples[i] ^ changed, i)'if wide else 'make_edges(u, samples[i] ^ changed)'
    old=f'                    sum += solve_edges({call});'
    assert old in fn
    fn=fn.replace(old,f'''                    const double value = solve_edges({call});
                    const double direct = value - q.value;
                    const double flip_new = solve_edges({flipped});
                    const u64 saved_opacity = opacity[k];
                    opacity[k] = cache_opacity[k];
                    const double flip_old = solve_edges({flipped});
                    opacity[k] = saved_opacity;
                    const int b = int(samples[i] >> changed_handle & 1);
                    last_owner_raw += direct;
                    last_owner_corrected += probability[changed_handle][b] * direct +
                        probability[changed_handle][b ^ 1] * (flip_new - flip_old);
                    sum += value;''')
    fn=fn.replace('        return sum / kSamples;', '''        last_owner_raw /= kSamples;
        last_owner_corrected /= kSamples;
        return sum / kSamples;''')
    p=p[:t]+fn+p[te:]
    old='''            if (viable && delta - weight * (next - profit) < -1e-9) {'''
    assert old in p
    p=p.replace(old,'''            const double correction = last_owner_corrected - last_owner_raw;
            if (viable && delta - weight * (next - profit + correction) < -1e-9) {
                accepted_owner_raw += last_owner_raw;
                accepted_owner_corrected += last_owner_corrected;
                accepted_donor += next - profit - last_owner_raw;''')
    s=s[:start]+p+s[end:]
    old='''    perforation.install();'''
    assert old in s
    s=s.replace(old,'''    std::cerr << "perf_owner_raw = " << perforation.accepted_owner_raw / P
              << "\\nperf_owner_conditioned = " << perforation.accepted_owner_corrected / P
              << "\\nperf_donor_gain = " << perforation.accepted_donor / P << '\\n';
    perforation.install();''')
    (out/'main.cpp').write_text(s)
    (out/'README.md').write_text(f'''改良元: solutions/esw-slim

D2の診断から得た穿孔差分の補正。{'元のhead穿孔だけを補正する。' if not wide else 'head穿孔と非head第2候補の追加穿孔を補正する（露出率0.125）。'}
変更紙自身の目標は、追加する穴の色の標本数が8または16しかない。
標本のその色を反転した場合の差分も計算し、列頭色の既存確率で重み付けする。
その他の窓と候補の順序、8標本、一次判定は維持する。
受理には補正した差分を使い、DPキャッシュは元の標本の値を維持する。

perf_owner_raw / perf_owner_conditionedは受理した変更の自目標の利益（補正前後、手/注文）。
perf_donor_gainは他目標の利益。既存のperforation指標も維持する。
{'ARGON_D2_RATE / WIDTH と d2_* はargon-des-perforationと同じ。'if wide else '追加の環境変数はない。'}
ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。
''')
