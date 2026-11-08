from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-next-prefix/main.cpp').read_text()
for name in ['wide','single']:
 s=base
 if name=='wide':
  s=s.replace('std::array<std::array<NextPrefix,32>,2>','std::array<std::array<NextPrefix,128>,2>')
  s=s.replace('(h^(h>>32))&31','(h^(h>>32))&127')
 else:
  s=s.replace('for(int level=1;level>=0;--level)','for(int level=1;level>=1;--level)')
  s=s.replace('if(phase<2 && end==64*(phase+1))','if(phase==1 && end==128)')
 s=s.replace('    std::cerr << "cf_value_hits = "', '    std::cerr << "next_prefix64 = " << solver.next_prefix64 << "\\nnext_prefix128 = " << solver.next_prefix128 << "\\n";\n    std::cerr << "cf_value_hits = "')
 p=r/'solutions'/('dcomp-prefix-'+name);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-next-prefix\n\n同一の途中状態cacheの'+('way数を32から128へ増やし衝突を減らす。' if name=='wide' else '64枚checkpointを省き128枚だけにして保存費用を減らす。')+'keyの完全比較と元の浮動小数点加算順は維持。next_prefix64/128に再利用数を出す。固定予算、ログ、DesignStore、実験スイッチを維持しfallbackなし。\n')
