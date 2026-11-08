from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
for mode in ['restrict','pad64','both']:
 s=base
 if mode in ('restrict','both'):
  a=s.index('AVX2_TARGET int evaluate_move(');b=s.index('\n// AS_PROFILE',a)
  t=s[a:b]
  for x,y in [('uint32_t* ndir','uint32_t* __restrict ndir'),('int* nrel','int* __restrict nrel'),('int* valid','int* __restrict valid'),('int* pending','int* __restrict pending'),('u64* closures','u64* __restrict closures'),('const pdir','__restrict const pdir'),('const prel','__restrict const prel'),('const pwit','__restrict const pwit'),('u64* f, u64* r','u64* __restrict f, u64* __restrict r'),('const u64* first','const u64* __restrict first'),('const u64* second','const u64* __restrict second')]:
   assert x in t,x;t=t.replace(x,y)
  s=s[:a]+t+s[b:]
 if mode in ('pad64','both'):
  assert s.count('while (n % 8) push(0, 0, 0, 0, 0, 0);')==1
  s=s.replace('while (n % 8) push(0, 0, 0, 0, 0, 0);','while (n % 64) push(0, 0, 0, 0, 0, 0);')
  assert s.count('const int end = std::min(n8, (block + 1) * 64);')==1
  s=s.replace('const int end = std::min(n8, (block + 1) * 64);','const int end = (block + 1) * 64;')
 p=r/'solutions'/('dcomp-map-'+mode);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n窓の移動評価の整数配列の配置・別名情報だけを変更。'+('互いに別allocationである入力状態と出力作業配列をrestrict指定する。' if mode in ('restrict','both') else '')+('無効な末尾を64要素境界まで埋め、内側loopを常に8 SIMDベクトルにする。追加laneは状態0のままで候補には入らない。' if mode in ('pad64','both') else '')+'\n\n乱数、予算、浮動小数点計算、列挙順序は不変。ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
