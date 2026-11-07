from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
for name,size in [('deval-colcache64',64),('deval-colcache256',256)]:
    s=base.replace('std::array<std::array<uint32_t, 16>, 64> colmdp_code_cache','std::array<std::array<uint32_t, '+str(size)+'>, 64> colmdp_code_cache',1)
    s=s.replace('std::array<std::array<float, 16>, 64> colmdp_value_cache','std::array<std::array<float, '+str(size)+'>, 64> colmdp_value_cache',1)
    shift=32-(size.bit_length()-1)
    s=s.replace('const int slot = (key ^ (key >> 9) ^ (key >> 17)) & 15;',f'const int slot = (key * 0x9e3779b9U) >> {shift};',1)
    d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(s)
    (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n注文計画の列MDP値キャッシュを各列16項から{size}項に広げ、乗算ハッシュで配置する。型列の完全キーを照合し、保存・計算する値は同じ。探索予算・時間ガードは変更しない。\n')
