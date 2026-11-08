from pathlib import Path
import re
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
for tag,key,value in [('rmin1','REPEAT_MIN','.1'),('rmin2','REPEAT_MIN','.2'),('alt075cut','NS_ALTERNATE_GAP','.75')]:
 pattern=r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";';m=re.search(pattern,B);assert m
 s=B[:m.start()]+f'if(std::strcmp(name,"{key}")==0)return "{value}";'+B[m.end():]
 d=R/'solutions'/('dcomp-t11-'+tag);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n追加探索への再配分のため、'+key+'='+value+'にする対照。実行時刻ではなく、各要求の既存費用改善幅だけで固定の反復条件を決める。両コンパイラの設定は同じ。既存ログ・profiler・trace・実験スイッチ・目次と段・DesignStoreを保持する。\n')
