from pathlib import Path
import re
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
# Every generic difference supplies one comparator edge. Its transitive
# reduction is a lower bound on generic differences, hence on 26-handle_diffs.
a=[(int(x,16),int(y)) for x,y in re.findall(r'0x([0-9a-f]+)ULL, (\d+)',b[b.index('constexpr PosetClass'):b.index('// kPosetDual')])]
off=b.index('constexpr int kPosetDual[318] = {')+len('constexpr int kPosetDual[318] = {')
d=[int(x) for x in re.findall(r'\d+',b[off:b.index('// clang-format on',off)])]
bound=0
for i,(bits,total) in enumerate(a):
 n=sum(1 for x in range(6) for y in range(6) if bits>>(8*x+y)&1 and not any((bits>>(8*x+z)&1) and (bits>>(8*z+y)&1) for z in range(6)))
 bound=max(bound,1800*(26-n)+5*(total+a[d[i]][1])+144*26)
assert bound==63444
(P/'radix-bound.txt').write_text(f'All 318 unlabeled partial orders: key <= {bound} < 65536.\n')
for name,small,prefix in [('deval-radix16',True,False),('deval-radix-prefix',True,True),('deval-prefix8',False,True)]:
 s=b
 if small:
  s=s.replace('std::array<int, 512> high{};','std::array<int, 256> high{};',1).replace('int min_high = 511, max_high = 0;','int min_high = 255, max_high = 0;',1)
  s=s.replace('''            // hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.
            assert(key < (1 << 17));''','''            // Generic differences dominate the closure's transitive reduction.
            // Exhausting the 318 poset classes bounds this integer key by 63444.
            assert(key < (1 << 16));''',1)
 if prefix:
  s=s.replace('struct WindowStats {',(P/'radix_prefix.inc').read_text()+'struct WindowStats {',1)
  s=s.replace('auto matching_cost = [&](const int* rel, u64 handle_mask) __attribute__((target("popcnt")))','auto matching_cost = [&](const int* rel, u64 handle_mask) __attribute__((target("popcnt,avx2")))',1)
  first=s.index('''        for (int i = 0, l = 0; i < 256; ++i) {''');last=s.index('''        for (int i = 0; i < size; i++) tmp''',first)
  s=s[:first]+'''        radix_prefix(low.data(),0,256);
        radix_prefix(high.data(),min_high,max_high+1);
'''+s[last:]
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n窓マッチングのradix整列を出力同一で軽くする。'+('318種類の部分順序の推移簡約を使い、整数費用の上限63444を確認したので、上位histogramを512から256項へ縮める。' if small else '')+('histogramの排他的累積和をAVX2整数8項ずつで行う。' if prefix else '')+'キー・同値順・貪欲選択・目的値・乱数列は同じ。全予算固定、時計による切り替えなし。\n')
 print(name,len(s.encode()))
