from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
def put(name,s,desc):
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n'+desc+'\n\n探索回数・候補順・演算順は同じで、時間による処理変更はない。\n');print(name,len(s.encode()))
old='        for (int k : order) if (col_of[k] >= 0 && !extra[k]) key[key_size++] = k;'
assert old in b
s=b.replace(old,'        for(int k:order) { key[key_size]=k; key_size += col_of[k]>=0 && !extra[k]; }',1)
put('deval-key-pack',s,'次注文コストのキャッシュキーを作る際、条件付き書込みを同じ位置への上書きと個数更新に置き換える。')
s=b.replace(old,'        for(int k=0;k<=kCapPaper;++k)extra[k]=true;\n        for(int k:order)if(!extra[k])key[key_size++]=k;',1)
put('deval-key-mask',s,'次注文コストのキャッシュキーで、汎用紙とcapも除外表にまとめる。走査中の列番号参照を省く。')
s=b.replace('std::array<uint32_t, 16>', 'std::array<uint32_t, 64>').replace('std::array<float, 16>', 'std::array<float, 64>')
s=s.replace('(key ^ (key >> 9) ^ (key >> 17)) & 15','(key ^ (key >> 9) ^ (key >> 17)) & 63',1)
put('deval-mdp-cache',s,'列MDPの正確な系列キーのキャッシュを16から64エントリへ広げる。衝突時は完全なキーを照合し、元の値を計算する。')
