from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'solver-tops/main.cpp').read_text()
needle='''                    prepare_visibility();
                    for(int t=mid_eject_mode==1?length:0;t<=first_illegal;t++){'''
replacement='''                    prepare_visibility();
                    int earliest=length+1,latest=-1;
                    for(int t=0;t<=first_illegal;t++)if(visible_at[t][k>>6]>>(k&63)&1){earliest=std::min(earliest,t);latest=t;}
                    for(int t=mid_eject_mode==1?length:0;t<=first_illegal;t++){
                        if(t!=earliest&&t!=latest)continue;'''
assert needle in s;s=s.replace(needle,replacement)
needle='        if(mid_eject_mode&&(only_eject||!mid_once)&&edits.size()>=2){'
assert needle in s;s=s.replace(needle,'        auto accepted_before_eject=mid_accepts;\n'+needle)
needle='        post_saved += int(input_ops.size()) - int(best_ops.size());'
assert needle in s;s=s.replace(needle,'''        if(mid_accepts>accepted_before_eject){
            edits=anchorize(best_ops);
            for(int pass=0;pass<3;pass++)if(!delete_singles())break;
        }
'''+needle)
s=s.replace('std::array<int,25>indices{};std::array<double,25>chance{};', 'std::array<int,64>indices;std::array<double,64>chance;')
s=s.replace('std::array<std::array<double,2>,26>left{},right{};left[0][0]=right[n][0]=1;', 'std::array<std::array<double,2>,65>left,right;left[0]={1,0};right[n]={1,0};')
(p/'main.cpp').write_text(s)
