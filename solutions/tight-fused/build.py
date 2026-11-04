from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
# Reuse the exact verified source transformations, with all production modes fixed.
for source in ['move-span','head-singles','post-fixed']:
 lines=(p.parent/source/'build.py').read_text().splitlines()
 assert lines[2].startswith("s=(p.parent/") and lines[-1]=="(p/'main.cpp').write_text(s)"
 scope={'s':s};exec('\n'.join(lines[3:-1]),scope);s=scope['s']
for old,field,value in [('static inline int move_mode=0;','int move_mode','2'),('static inline int fast_single_tables=0;','int fast_single_tables','1'),('static inline bool fixed_lists=false;','bool fixed_lists','true')]:
 assert s.count(old)==1
 s=s.replace(old,'\n#ifdef FUSED_RESEARCH\n'+old+'\n#else\nstatic constexpr '+field+'='+value+';\n#endif\n')
(p/'main.cpp').write_text(s)
