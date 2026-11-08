from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
s='#define COLFAST_PROFILE 1\n'+s
s=s.replace('CfProfile cf_next_cost{"next_cost"};','CfProfile cf_next_cost{"next_cost"};\nCfProfile cf_next_key{"next_key"},cf_next_scan{"next_scan"},cf_next_holes{"next_holes"},cf_next_mdp{"next_mdp"};')
s=s.replace('&cf_plan_cost, &cf_filler_charge,','&cf_plan_cost, &cf_next_key, &cf_next_scan, &cf_next_holes, &cf_next_mdp, &cf_filler_charge,')
a=s.index('    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost(');b=s.index('    // Lexicographic permutation rank',a)
t=s[a:b]
t=t.replace('        int key_size = 0;','        int key_size = 0;\n        double key_clock=elapsed_sec();')
t=t.replace('        NextValueEntry& cached =', '        cf_next_key.inclusive+=elapsed_sec()-key_clock;++cf_next_key.calls;\n        NextValueEntry& cached =')
t=t.replace('        cf_value_misses++;','        cf_value_misses++;\n        double scan_clock=elapsed_sec();')
t=t.replace('        // covered[c][color]:','        cf_next_scan.inclusive+=elapsed_sec()-scan_clock;++cf_next_scan.calls;\n        double holes_clock=elapsed_sec();\n        // covered[c][color]:')
t=t.replace('        if (mdp_scan)\n            cost +=','        cf_next_holes.inclusive+=elapsed_sec()-holes_clock;++cf_next_holes.calls;\n        double mdp_clock=elapsed_sec();\n        if (mdp_scan)\n            cost +=')
t=t.replace('        cached.size = key_size;','        cf_next_mdp.inclusive+=elapsed_sec()-mdp_clock;++cf_next_mdp.calls;\n        cached.size = key_size;')
s=s[:a]+t+s[b:]
p=r/'solutions/dcomp-next-prof';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\nnext_costの鍵、列内scan、穴費用、MDPの時間を既存scaled clockで追加計測する。演算・出力は不変。COLFAST_PROFILEも有効。計測版の時間を高速化の成果には使わない。\n')
