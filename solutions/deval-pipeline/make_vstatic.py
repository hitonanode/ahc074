from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-ordered8/main.cpp').read_text()
old='''        for(int power=0;power<4;++power)out[key+"_d"+std::to_string(power)]=0;
        for(int band:{1,2,3,5})out[key+"_last"+std::to_string(band)]=0;
        out[key+"_balance"]=0;out[key+"_balance2"]=0;'''
new='''        // std::map nodes stay valid: bind each feature once, preserving every
        // floating-point update and the original column order.
        std::array<double*,10> acc{};
        for(int power=0;power<4;++power)acc[power]=&out[key+"_d"+std::to_string(power)];
        const int bands[4]={1,2,3,5};
        for(int j=0;j<4;++j)acc[j+4]=&out[key+"_last"+std::to_string(bands[j])];
        acc[8]=&out[key+"_balance"];acc[9]=&out[key+"_balance2"];
        for(auto p:acc)*p=0;'''
assert old in s;s=s.replace(old,new,1)
old='''            for(int power=0;power<4;++power){out[key+"_d"+std::to_string(power)]+=v;v*=depth[c];}
            for(int band:{1,2,3,5})if(c>=s.H-band)out[key+"_last"+std::to_string(band)]+=h;
            out[key+"_balance"]+=h*balance[c];out[key+"_balance2"]+=h*balance[c]*balance[c];'''
new='''            for(int power=0;power<4;++power){*acc[power]+=v;v*=depth[c];}
            for(int j=0;j<4;++j)if(c>=s.H-bands[j])*acc[j+4]+=h;
            *acc[8]+=h*balance[c];*acc[9]+=h*balance[c]*balance[c];'''
assert old in s;s=s.replace(old,new,1)
old='''    for(int t=0;t<P;++t) {
        const auto [gc,nrel]=gt.cost(s,t);'''
new='''    double &sum_gc=out["gc"],&sum_holes=out["holes"],&sum_extra=out["extra_holes"];
    for(int t=0;t<P;++t) {
        const auto [gc,nrel]=gt.cost(s,t);'''
assert old in s;s=s.replace(old,new,1)
old='''        out["gc"]+=gc/P;out["holes"]+=a[3]/P;out["extra_holes"]+=a[4]/P;'''
new='''        sum_gc+=gc/P;sum_holes+=a[3]/P;sum_extra+=a[4]/P;'''
assert old in s;s=s.replace(old,new,1)
p=R/'solutions/deval-vstatic';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\nVの静的特徴量の集計で、同じ特徴名の文字列生成とmap検索を列・目標ごとに繰り返すのを省く。map内の値への参照をループ前に用意する。浮動小数点の更新式と順序、特徴量・予測・候補の選択を保つ。全予算固定、時間による切り替えなし。\n')
print(len(s.encode()))
