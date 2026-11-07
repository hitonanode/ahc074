from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-free-late/main.cpp').read_text()
code='''        // A singleton head can change color now. Linear proposals must charge
        // its old color's replacement, and credit a new head only if it wins.
        const auto selected=head.heads();
        std::vector<double> backup(d.U);
        if(search_mode&8)for(int i=0;i<d.U;++i)if(anchor[i]<0 && head.beta[i])
            for(int j=0;j<d.U;++j)if(j!=i && d.unit[j].c==d.unit[i].c &&
                d.color(d.unit[j],d.unit[j].c)==color[i])backup[i]=std::max(backup[i],head.utility[j]);
        auto donor_profit=[&](int i,int b,double value) {
            const int c=d.unit[i].c,cl=d.hb[b]>>c&1;
            if(!(search_mode&8)ONLY_FLIP)return head.beta[i]*value;
            if(cl==color[i])return head.beta[i]*std::max(value,backup[i]);
            const int y=selected[c][cl];
            return head.beta[i]*backup[i]+(d.weight(d.unit[y])==1 ?
                head.prob[c][cl]*std::max(0.,value-head.utility[y]):0.);
        };
'''
needle='''        // cost[i][j]: the mobile target of unit j in unit i (with i's anchor, column and color)'''
for name,flip in [('deval-free-head',False),('deval-free-flip',True)]:
    s=b.replace(needle,code.replace('ONLY_FLIP',' || cl==color[i]' if flip else '')+needle,1)
    # Only singleton donor terms; pair anchor/color compatibility is unchanged.
    start=s.index('                } else {\n                    // Only mobile targets')
    end=s.index('                cost[i][j] = v - weight * profit;',start)
    q=s[start:end]
    assert q.count('head.beta[i] * head.donor(u, i)')==1
    assert q.count('head.beta[i] * value')==1
    q=q.replace('head.beta[i] * head.donor(u, i)','donor_profit(i,b,head.donor(u,i))').replace('head.beta[i] * value','donor_profit(i,b,value)')
    s=s[:start]+q+s[end:];s=s.replace('const int extra_mode=4;','const int extra_mode=12;',1)
    p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
    (p/'README.md').write_text('改良元: `solutions/deval-free-late`。\n\n色変更を許した単独の代表紙について、Hungarianの線形提案でfiller価値を補正する。色を替えると旧色の代表は次点の紙になり、新色には既存代表より価値が高い場合だけ貢献する。この差を同じ頭確率で評価する。'+('同色の置換は従来通り。' if flip else '同色の置換でも次点の代表紙が残ることを反映する。')+'巡回の受理は従来の正確な仕上げ目的、完成8候補の選択はVのまま。探索回数・候補数は固定、時間不足の切り替えなし。\n')
    print(name,len(s.encode()))
