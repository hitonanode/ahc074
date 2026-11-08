"""Pack the 30 relation bits directly, rather than transpose an 8x8 matrix."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-nine/main.cpp').read_text()
a='''    return uint32_t(_pext_u64(c, kUpperPairs)) | uint32_t(_pext_u64(transpose8(c), kUpperPairs)) << 16;'''
b='''    // Extract the five lower-triangle columns in edge order, directly.
    // This is exactly pext(transpose8(c),kUpperPairs), including unused bits.
    const uint32_t reverse=uint32_t(_pext_u64(c,0x0000010101010100ULL))
        |uint32_t(_pext_u64(c,0x0000020202020000ULL))<<5
        |uint32_t(_pext_u64(c,0x0000040404000000ULL))<<9
        |uint32_t(_pext_u64(c,0x0000080800000000ULL))<<12
        |uint32_t((c>>44)&1)<<14;
    return uint32_t(_pext_u64(c,kUpperPairs))|(reverse<<16);'''
assert s.count(a)==1
p=root/'solutions/dcomp-nine-packrel';p.mkdir(exist_ok=True)
(p/'main.cpp').write_text(s.replace(a,b))
(p/'README.md').write_text('''改良元: solutions/dcomp-nine

窓探索のPosetSums検索キーを、8×8ビット行列の転置を経由せず、下三角の列から直接PEXTで取り出す。30本の有向辺とその順序は厳密に同じ。一般のtranspose8関数や他の利用箇所は保持する。

探索回数、乱数列、9候補、評価式、注文処理、CLOCK_SCALE、ログ、実験スイッチとプロファイラはそのまま。近似演算・時間による処理の切替なし。
''')
# The transform is a linear bit selection: equality on every basis bit proves
# equality for all 64-bit inputs, not just acyclic relation matrices.
def pext(x,m):
    y=0;i=0
    while m:
        bit=m&-m
        if x&bit:y|=1<<i
        i+=1;m-=bit
    return y
def transpose(x):
    return sum(((x>>(8*i+j))&1)<<(8*j+i) for i in range(8) for j in range(8))
for bit in range(64):
    c=1<<bit
    a=pext(transpose(c),0x2030383c3e)
    b=(pext(c,0x10101010100)|(pext(c,0x20202020000)<<5)
       |(pext(c,0x40404000000)<<9)|(pext(c,0x80800000000)<<12)|(((c>>44)&1)<<14))
    assert a==b,(bit,a,b)
print('pack_relation: all 64 basis bits identical')
