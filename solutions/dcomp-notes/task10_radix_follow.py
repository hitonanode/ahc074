from pathlib import Path
r=Path(__file__).resolve().parents[2]
for name,parent,bits,shift in [('dcomp-radix5','dcomp-hole4',5,32),('dcomp-key32-r6','dcomp-key32',6,15),('dcomp-key32-r7','dcomp-key32',7,15)]:
 s=(r/'solutions'/parent/'main.cpp').read_text();a=s.index('    auto matching_cost =');b=s.index('        // The greedy without branches',a);t=s[a:b]
 for x,y in [('std::array<int, 256> low{};',f'std::array<int, {1<<bits}> low{{}};'),('std::array<int, 512> high{};',f'std::array<int, {1<<(17-bits)}> high{{}};'),('int min_high = 511, max_high = 0;',f'int min_high = {(1<<(17-bits))-1}, max_high = 0;'),('low[key & 255]++',f'low[key & {(1<<bits)-1}]++'),('key >> 8',f'key >> {bits}'),('radix_prefix(low.data(),0,256)',f'radix_prefix(low.data(),0,{1<<bits})'),(f'(keyed[i] >> {shift}) & 255',f'(keyed[i] >> {shift}) & {(1<<bits)-1}'),(f'tmp[i] >> {shift+8}',f'tmp[i] >> {shift+bits}')]:
  assert x in t,x;t=t.replace(x,y)
 s=s[:a]+t+s[b:];p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/'+parent+'\n\n安定radix sortの桁を'+str(bits)+'+'+str(17-bits)+' bitに分ける。'+('32bitの費用/ペアレコード圧縮と組み合わせる。' if shift==15 else '')+'費用・同点順・予算・乱数・要求処理は不変。ログ・profiler・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
