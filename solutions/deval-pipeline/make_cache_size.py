from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
for name,n,e in [('deval-cache-next1k',1024,128),('deval-cache-end512',256,512),('deval-cache-both1k',1024,512)]:
 s=b.replace('std::array<NextValueEntry, 256> next_value_cache',f'std::array<NextValueEntry, {n}> next_value_cache',1)
 s=s.replace('std::array<EndMemo, 128> end_memo',f'std::array<EndMemo, {e}> end_memo',1)
 p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-ordered8`。\n\n注文末尾の値キャッシュを{n}件、後処理の完全後続配列キャッシュを{e}件とする。完全なキー照合と同じ浮動小数点演算順を保ち、衝突による再計算だけを減らす。探索量・候補・制限は同じで、時計による切り替えなし。\n')
 print(name,len(s.encode()))
