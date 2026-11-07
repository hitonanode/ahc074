from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
start=b.index('    auto matching_cost =')
end=b.index('    // ==== Window assignment: candidate screens and tables ====',start)
for bits in [8,9,10]:
 name=f'deval-sort-msd{bits}';body=b[start:end]
 body=body.replace('        std::array<int, 256> low{};\n','',1)
 body=body.replace('std::array<int, 512> high{};',f'std::array<int, {1<<(17-bits)}> high{{}};',1)
 body=body.replace('int min_high = 511, max_high = 0;',f'int min_high = {(1<<(17-bits))-1}, max_high = 0;',1)
 body=body.replace('            low[key & 255]++;\n','',1).replace('key >> 8',f'key >> {bits}')
 pos=body.index('        for (int i = 0, l = 0; i < 256; ++i) {');last=body.index('        for (int i = min_high',pos)
 body=body[:pos]+body[last:]
 old='''        for (int i = 0; i < size; i++) tmp[low[(keyed[i] >> 32) & 255]++] = keyed[i];
        for (int i = 0; i < size; i++) sorted[high[tmp[i] >> 40]++] = tmp[i];'''
 assert old in body
 body=body.replace(old,f'''        // Partition by the high key first. Each short bucket is ordered by
        // the complete integer key, including its original pair-index tie.
        for(int i=0;i<size;++i)sorted[high[keyed[i]>>{32+bits}]++]=keyed[i];
        for(int bucket=min_high,begin=0;bucket<=max_high;++bucket) {{
            const int end=high[bucket];
            std::sort(sorted.begin()+begin,sorted.begin()+end);
            begin=end;
        }}''',1)
 s=b[:start]+body+b[end:]
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n窓割当てのマッチング前の整数キー整列を、下位8 bitからの2段radixから、上位{17-bits} bitで分けた小区間ごとの整列へ置き換える。比較する完全な64 bitキーとペア番号による同値順は同じ。費用・貪欲マッチング・乱数・探索回数は変えない。\n')
 print(name,len(s.encode()))
