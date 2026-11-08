"""Create the final compiler-selected exact control and fixed-budget request candidate."""
from pathlib import Path
import argparse,hashlib,json,datetime
p=argparse.ArgumentParser();p.add_argument('--gcc-parent',required=True);p.add_argument('--clang-parent',default='dcomp-key32-r7');a=p.parse_args();r=Path(__file__).resolve().parents[2]
def read(n):return (r/'solutions'/n/'main.cpp').read_text()
def region(s):
 a=s.index('    // Only `valid[0..nvalid)` is traversed here.');b=s.index('    // the pairs (ndir, nrel, valid);',a);return a,b
s=read('dcomp-hole4');g=read(a.gcc_parent);c=read(a.clang_parent);sa,sb=region(s);ga,gb=region(g);ca,cb=region(c)
s=s[:sa]+'    // Same stable cost/tie order, with the measured layout for each compiler.\n#if defined(__clang__)\n'+c[ca:cb]+'#else\n'+g[ga:gb]+'#endif\n'+s[sb:]
base=s
for name,spend in [('dcomp-combo-fast',False),('dcomp-combo-alt1',True)]:
 s=base
 if spend:
  x='        if(const char* value=std::getenv(local.c_str()))return value;';assert s.count(x)==1;s=s.replace(x,x+'\n        if(std::strcmp(name,"NS_ALTERNATE")==0)return "1";\n        if(std::strcmp(name,"NS_ALTERNATE_GAP")==0)return "1.0";')
  x='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "5";';assert s.count(x)==1;s=s.replace(x,x.replace('"5"','"6"'))
  x='                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);';assert s.count(x)==1;s=s.replace(x,x.replace(', 4);',', 2);'))
 d=r/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/combo-m1-nine\n\n設計は同じ9候補を生成・選択する。窓のsparsebitsはGCCでだけ使い、Clangでは元の関係走査。互換ペアの安定sortはGCCに'+a.gcc_parent+'、Clangに'+a.clang_parent+'の配置を使い、費用・同点順を保つ。rematch donorの修復可能maskを4対象ずつ計算し、Hungarianの前駆列を同じmaskで更新する。\n\n注文処理では、後の手と交換できるanchor群のリンク・合法性再生を共有し、取り出し修復が既に持つ終状態と表示条件を再利用する。空の修復区間では深い順序を構成しない。next_costは先頭64/128枚の正確な途中状態を完全keyで保存し、穴費用の4項だけを同時計算する。浮動小数点の加算順は保ち、fast-mathは使わない。\n\n'+('空いた時間を別プランの再編集に配る。NS_ALTERNATE=1、NS_ALTERNATE_GAP=1.0、alternateの取り出し修復は最大2回。NEUTRAL_WIDTH=6、POST_CANDIDATES=6、NS_ROUNDS=3、NEUTRAL_SLACK=.35。元のF3_*環境変数の実験設定を優先する。' if spend else '注文予算も親と同じ。出力同一の速度比較用の対照版。')+'\n\n全予算は固定回数。時間不足の軽いモード、設計cap、時刻による候補数変更はない。DesignStoreは選択した設計を保存する。段の目印と目次、ログ・metrics・@paper/@ops・trace・profiler・実験スイッチを維持する。検証手順と式の根拠は ../dcomp-notes/EXACTNESS10.md、実測結果は ../dcomp-notes/REPORT10.md。\n')
 info={'created_at':datetime.datetime.now().astimezone().isoformat(),'gcc_sort':a.gcc_parent,'clang_sort':a.clang_parent,'sha256':hashlib.sha256(s.encode()).hexdigest(),'bytes':len(s.encode()),'source':str(d/'main.cpp')}
 (r/'solutions/dcomp-notes'/f't10-release-{name}.json').write_text(json.dumps(info,indent=2)+'\n');print(name,info)
