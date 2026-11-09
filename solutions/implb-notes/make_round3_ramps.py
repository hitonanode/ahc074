from pathlib import Path
base=Path('solutions/d30a-reset6/main.cpp').read_text()
for name,values in [('ramp-a',[2.,4.,6.,6.]),('ramp-b',[6.,6.,10.,10.])]:
 path=Path('solutions/d30b-'+name);path.mkdir(exist_ok=False)
 helper='''    // Use absolute segment indices across the shared prefix and every branch.
    // Finishing calls refresh_reset() without an index and keeps reset_strength=6.
    static double segment_reset_strength(int segment) {
        assert(segment >= 0 && segment < 4);
#ifdef LOCAL_BENCH
        static const bool enabled = env_real("D30B_RESET_RAMP", 1) != 0;
        static const std::array<double, 4> strengths{'''+', '.join(f'env_real("D30B_RESET_S{i}", {v})' for i,v in enumerate(values))+'''};
        return enabled ? strengths[segment] : reset_strength;
#else
        static constexpr std::array<double, 4> strengths{'''+', '.join(map(str,values))+'''};
        return strengths[segment];
#endif
    }
'''
 old='''    void refresh_reset() {
        for (int c = 0; c < H; c++) reset_targets[c] = float(reset_strength * nt[c]);
        rebuild();
    }'''
 new=helper+'''    void refresh_reset(int segment = -1) {
        const double strength = segment < 0 ? reset_strength : segment_reset_strength(segment);
        for (int c = 0; c < H; c++) reset_targets[c] = float(strength * nt[c]);
        rebuild();
    }'''
 assert base.count(old)==1;s=base.replace(old,new)
 old='''        for (int s = firstSegment; s < endSegment; s++) {
            refresh_reset();''';assert s.count(old)==1
 s=s.replace(old,'''        for (int s = firstSegment; s < endSegment; s++) {
            refresh_reset(s);''')
 old='    deval::DesignValue value;';assert s.count(old)==1
 s=s.replace(old,'''#ifdef LOCAL_BENCH
    for (int segment = 0; segment < 4; ++segment)
        std::cerr << "ramp_reset_s" << segment << " = " << Design::segment_reset_strength(segment) << '\\n';
    std::cerr << "ramp_finish_reset = " << Design::reset_strength << '\\n';
#endif
'''+old)
 (path/'main.cpp').write_text(s)
 (path/'README.md').write_text('改良元: solutions/d30a-reset6\n\n焼きなましの4区間に使うreset需要の倍率を '+str(values)+' とする。共有前半と枝の後半は元の絶対区間番号を使い、反復回数・温度・乱数消費は変更しない。仕上げのfiller_climbとrematchは従来の6を使う。色確率や穿孔の倍率、Vは変更しない。\n\nLOCAL_BENCHではD30B_RESET_RAMP=0で全区間を基準の6へ戻せる。D30B_RESET_S0〜S3で各区間の倍率を指定できる。既存D30A_RESETも維持する。新しいstderr指標ramp_reset_s0〜s3は区間倍率、ramp_finish_resetは仕上げ倍率。固定反復、CLOCK_SCALE、DesignStore、既存注釈と段目次を維持し、新しい時計・打切りは追加しない。\n')
 print(path)
