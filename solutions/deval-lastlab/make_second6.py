from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
def emit(n,t,d,base='deval-trim6b'):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(t)
 (p/'README.md').write_text('改良元: `solutions/'+base+'`。\n\n'+d+'\n\n最初の4候補と完成候補のVによる選択は維持する。追加処理も固定回数で、時間による切替えはない。ログ・実験スイッチ・DesignStoreを維持する。\n')
 assert len(t.encode())<=522000,(n,len(t.encode()))
 print(n,len(t.encode()))
x=(root/'solutions/deval-unit-warm/main.cpp').read_text()
x=x.replace('const int extra_mode=4|(whole_units?8:0);','const int extra_mode=4;').replace('    const bool whole_units=extra==2;\n','')
x=x.replace('rematch_probability(*des, extra?1:2, 1.0, 2.0);','rematch_probability(*des, extra?1:2, 1.0, 2.0, nullptr, extra?12:0);')
emit('deval-unit-before',x,'cold再仕上げ2回だけ、穴あけ前の再割当てで紙全体を入れ替える。単独/ペア構成と色をslotに固定しない。以後の穴あけと通常の最終再割当てで、新しい配置に穴を合わせる。warm2回の処理は元に戻す。','deval-unit-warm')
for count in [100000,300000]:
 x=s.replace('        if(warm)warm_state=state;','''        if(!warm) {
            // Reopen the full native neighborhood before printing fresh masks.
            const double begin=elapsed_sec();des->anneal_reheat=1.;
            des->anneal(1e300,'''+str(count*4)+''',3,4);
            anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        }
        if(warm)warm_state=state;''')
 emit('deval-reanneal'+str(count//1000),x,f'cold再仕上げ2回の前に、従来のanneal目的と最後の温度区間で{count}提案を追加する。ペア組合せ・列サイズ・ハンドル順序も通常の近傍で動かせる。穴はその後の仕上げで作り直す。')
