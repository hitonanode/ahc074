from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-hole4/main.cpp').read_text()
for bits in [6,7,9]:
 s=base;a=s.index('    auto matching_cost =');b=s.index('        // The greedy without branches',a);t=s[a:b]
 changes={'std::array<int, 256> low{};':f'std::array<int, {1<<bits}> low{{}};','std::array<int, 512> high{};':f'std::array<int, {1<<(17-bits)}> high{{}};','int min_high = 511, max_high = 0;':f'int min_high = {(1<<(17-bits))-1}, max_high = 0;','low[key & 255]++':f'low[key & {(1<<bits)-1}]++','key >> 8':f'key >> {bits}','radix_prefix(low.data(),0,256)':f'radix_prefix(low.data(),0,{1<<bits})','(keyed[i] >> 32) & 255':f'(keyed[i] >> 32) & {(1<<bits)-1}','tmp[i] >> 40':f'tmp[i] >> {32+bits}'}
 for x,y in changes.items():assert x in t,x;t=t.replace(x,y)
 s=s[:a]+t+s[b:]
 p=r/'solutions'/f'dcomp-radix{bits}';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: solutions/dcomp-hole4\n\n窓探索のmatching_costにある安定2段radix sortの桁分割を8+9 bitから{bits}+{17-bits} bitへ変える。17bitの費用と元のpair番号の同点順は同じ。prefix和と2回の安定scatterはそのまま。要求処理・候補・乱数・予算を変更しない。ログ、profiler、実験スイッチ、DesignStoreを維持、時間fallbackなし。\n')
