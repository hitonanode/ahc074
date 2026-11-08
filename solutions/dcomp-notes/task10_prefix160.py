from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-next-prefix/main.cpp').read_text()
for a,b in [('std::array<uint8_t,128> key;','std::array<uint8_t,160> key;'),('if(i==120)prefix_hash[1]=hash;','if(i==152)prefix_hash[1]=hash;'),('if(in_place>128) {','if(in_place>64) {'),('const int length=64*(level+1);','const int length=level?160:64;\n                if(length>=in_place)continue;'),('const int end=phase<2?std::min(in_place,64*(phase+1)):in_place;','const int end=phase<2?std::min(in_place,phase?160:64):in_place;'),('if(phase<2 && end==64*(phase+1)) {','if(phase<2 && end==(phase?160:64)) {')]:
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
s=s.replace('after 64/128 terms','after 64/160 terms')
p=r/'solutions/dcomp-next-prefix160';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-next-prefix\n\n同じ正確な途中状態cacheのcheckpointを64/128枚から64/160枚へ変える。加算順はそのまま、共通prefixが深い場合の省略量を増やす。予算・モデル値・ログ・DesignStore・実験スイッチを維持。\n')
