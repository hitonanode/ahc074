from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
for n in [64,128]:
 s=base
 for a,b in [('std::array<std::array<uint32_t, 16>, 64> colmdp_code_cache',f'std::array<std::array<uint32_t, {n}>, 64> colmdp_code_cache'),('std::array<std::array<float, 16>, 64> colmdp_value_cache',f'std::array<std::array<float, {n}>, 64> colmdp_value_cache'),('const int slot = (key ^ (key >> 9) ^ (key >> 17)) & 15;',f'const int slot = (key ^ (key >> 9) ^ (key >> 17)) & {n-1};')]:
  assert s.count(a)==1;s=s.replace(a,b)
 s=s.replace('retains 16 exact keys/values',f'retains {n} exact keys/values')
 p=r/'solutions'/f'dcomp-mdpways{n}';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: solutions/dcomp-screen-replay\n\n列MDPの正確なtype列cacheを列ごと16から{n}項目へ拡大して衝突を減らす。keyは衝突のない長さ付き2bit列、値は元のfloatをそのまま保持。計算式、浮動小数点、固定予算、ログ、実験スイッチ、DesignStoreは不変。時間fallbackなし。\n')
