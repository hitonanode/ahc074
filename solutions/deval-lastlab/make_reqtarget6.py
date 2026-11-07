from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
marker='// ==== Solver: papers, handles and the generic look-ahead ===='
end='// ==== Emergency design ===='
assert s.count(marker)==s.count(end)==1
for suffix,target in [('pop','popcnt'),('avx','avx2,popcnt')]:
    name='deval-reqtarget-'+suffix
    x=s.replace(marker,f'''#if defined(__clang__)
#pragma clang attribute push (__attribute__((target("{target}"))), apply_to=function)
#elif defined(__GNUC__)
#pragma GCC target("{target}")
#endif
'''+marker)
    x=x.replace(end,'''#ifdef __clang__
#pragma clang attribute pop
#endif
'''+end)
    p=root/'solutions'/name;p.mkdir()
    (p/'main.cpp').write_text(x)
    (p/'README.md').write_text(f'''改良元: `solutions/deval-trim6b`。

Solverの関数群にtarget("{target}")を明示する。後処理のビット数集計をハードウェア命令で行い、{'配列コピーにもAVX2命令を使えるようにする。' if suffix=='avx' else 'その他の命令指定は変えない。'}FMAとfast-mathを新たに有効化しない。GCCは既存のpush/pop_options内、Clangはattribute push/popで範囲を限定する。探索予算・乱数・演算の式・実験スイッチ・ログは維持する。出力一致と通常24並列のcompareで効果を確認する実験。
''')
    assert len(x.encode())<=522000
    print(name,len(x.encode()))
