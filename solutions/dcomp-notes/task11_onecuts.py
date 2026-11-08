from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
for name,desc in [('early','1→1の挿入時点を最も早い合法時点だけにする'),('late','1→1の挿入時点を最も遅い合法時点だけにする'),('deep','1→1の現在のanchor候補のうち最も深いものだけを試す'),('shallow','1→1の現在のanchor候補のうち最も浅いものだけを試す')]:
 s=B
 if name in ['early','late']:
  a='''                    for (int pass = 0; pass < (earliest == latest ? 1 : 2); pass++) {
                        const int t = pass ? latest : earliest;''';assert s.count(a)==1
  rule='if(removed==1 && pass)break;'if name=='early'else'if(removed==1 && !pass && earliest!=latest)continue;'
  s=s.replace(a,a.replace('                        const int t',f'                        {rule}\n                        const int t'))
 else:
  a='''                        bool prepared_screen=false;
                        for (int ai = 0; ai < count; ai++) {''';assert s.count(a)==1
  relation='>'if name=='deep'else'<'
  s=s.replace(a,'''                        int selected_anchor=0;
                        if(removed==1)for(int a=1;a<count;++a) {
                            const int x=anchors[a]<0?-1:ord_position[anchors[a]];
                            const int y=anchors[selected_anchor]<0?-1:ord_position[anchors[selected_anchor]];
                            if(x'''+relation+'''y)selected_anchor=a;
                        }
                        bool prepared_screen=false;
                        for (int ai = 0; ai < count; ai++) {
                            if(removed==1 && ai!=selected_anchor)continue;''')
 d=R/'solutions'/('dcomp-t11-one-'+name);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'。2→1修復は元のまま。選択は状態と固定の規則だけで決め、時刻は使わない。深さ制限は紙IDではなく、候補完成stack内のanchor位置で比較する。\n\n追加親の最早挿入制限で時間あたりの損が小さかったため、主親側の価格を測る対照。両コンパイラ共通の固定予算。ログ・trace・profiler・既存実験スイッチ・目次と段・DesignStoreを保持する。\n')
