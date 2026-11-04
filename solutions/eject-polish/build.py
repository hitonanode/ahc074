from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-lean/main.cpp').read_text()
s=s.replace('    static inline bool mid_once=true;', '    static inline int polish_mode=0;\n    long long polish_calls=0;\n    static inline bool mid_once=true;')
needle='        if(mid_eject_mode&&mid_once)chosen_path=post_optimize(st0,std::move(chosen_path),u,true);'
assert needle in s;s=s.replace(needle,'''        auto before_eject=mid_accepts;
'''+needle+'''
        if(polish_mode&&mid_accepts>before_eject){
            if(polish_mode==1||polish_mode==3){chosen_path=post_optimize(st0,std::move(chosen_path),u,false);polish_calls++;}
            if(polish_mode>=2){
                for(int iteration=0;iteration<(polish_mode==4?2:1);iteration++){
                    auto before=mid_accepts;
                    chosen_path=post_optimize(st0,std::move(chosen_path),u,true);polish_calls++;
                    if(mid_accepts==before)break;
                }
            }
        }''')
(p/'main.cpp').write_text(s)
