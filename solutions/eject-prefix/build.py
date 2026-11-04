from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-lazy/main.cpp').read_text()
s=s.replace('    static inline bool mid_once=true;', '    static inline int prefix_mode=0;\n    static inline bool mid_once=true;')
needle='''                    prepare_visibility();
                    for(int t=mid_eject_mode==1?length:0;t<=first_illegal;t++){'''
replacement='''                    prepare_visibility();
                    int earliest=length+1,latest=-1;
                    std::array<int,K+1> after_anchor;after_anchor.fill(length+1);
                    for(int t=0;t<=first_illegal;t++)if(visible_at[t][k>>6]>>(k&63)&1){earliest=std::min(earliest,t);latest=t;}
                    if(prefix_mode>=3)for(int a:anchors){
                        int cut=0;for(int t=0;t<length;t++)if(trial[t].paper==a)cut=t+1;
                        for(int t=cut;t<=first_illegal;t++)if(visible_at[t][k>>6]>>(k&63)&1){after_anchor[a+1]=t;break;}
                    }
                    for(int t=mid_eject_mode==1?length:0;t<=first_illegal;t++){
                        if(prefix_mode==1&&t!=earliest)continue;
                        if(prefix_mode==2&&t!=earliest&&t!=latest)continue;'''
assert needle in s;s=s.replace(needle,replacement)
needle='''                        for(int a:anchors){
                            auto next=trial;'''
assert needle in s
s=s.replace(needle,'''                        for(int a:anchors){
                            if(prefix_mode==3&&t!=after_anchor[a+1])continue;
                            if(prefix_mode==4&&t!=earliest&&t!=after_anchor[a+1])continue;
                            auto next=trial;''')
(p/'main.cpp').write_text(s)
