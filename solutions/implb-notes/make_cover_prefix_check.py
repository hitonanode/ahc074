from pathlib import Path
import sys
source=Path(sys.argv[1]);s=source.read_text()
p=Path('solutions/d30b-cover-prefix-check');p.mkdir(exist_ok=False)
old='#ifdef NEXT_PREFIX_CHECK\n    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost_reference'
new='''#ifdef NEXT_PREFIX_CHECK
    inline static long long prefix_check_calls = 0, prefix_check_bit_differences = 0;
    inline static double prefix_check_max_abs = 0;
    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost_reference'''
assert s.count(old)==1;s=s.replace(old,new)
old='''        if(std::bit_cast<u64>(reference)!=std::bit_cast<u64>(cost)) {
            std::cerr<<"NEXT_PREFIX_MISMATCH "<<std::hexfloat<<reference<<' '<<cost<<'\\n';std::abort();
        }'''
new='''        ++prefix_check_calls;
        prefix_check_bit_differences += std::bit_cast<u64>(reference) != std::bit_cast<u64>(cost);
        const double error = std::abs(reference - cost);
        prefix_check_max_abs = std::max(prefix_check_max_abs, error);
        // Decimal cover strengths lose the original exact binary-grid property.
        // The diagnostic still rejects differences larger than 64 eps * (1+|reference|).
        if (!(error <= 0x1p-46 * (1 + std::abs(reference)))) {
            std::cerr<<"NEXT_PREFIX_MISMATCH "<<std::hexfloat<<reference<<' '<<cost<<'\\n';std::abort();
        }'''
assert s.count(old)==1;s=s.replace(old,new)
old='    // ==== main: statistics ===='
new=old+'''
#ifdef NEXT_PREFIX_CHECK
    std::cerr << "prefix_check_calls = " << Solver::prefix_check_calls
              << "\\nprefix_check_bit_differences = " << Solver::prefix_check_bit_differences
              << "\\nprefix_check_max_abs = " << Solver::prefix_check_max_abs << '\\n';
#endif'''
assert s.count(old)==1;s=s.replace(old,new)
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/d30a-reset6\n\n診断専用。'+str(source.parent)+'と同じcover係数を使い、NEXT_PREFIX_CHECKでSIMDと参照計算の誤差を測る。通常版の採否や時間測定には使わない。\n\n元のcheckはbit完全一致だが、非二進分数のcover係数では厳密格子の前提を失う。bit差の件数と絶対誤差最大を記録し、64*double epsilon*(1+abs(reference))を超える誤差で停止する。stderrはprefix_check_calls、prefix_check_bit_differences、prefix_check_max_abs。乱数・反復数・出力選択は変更しない。NEXT_PREFIX_CHECK以外では追加計算しない。\n')
