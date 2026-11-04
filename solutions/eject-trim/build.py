from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-lazy/main.cpp').read_text()
s=s.replace('    static inline bool mid_once=true;', '    static inline bool trim_after=true;\n    static inline bool mid_once=true;')
needle='        if(mid_eject_mode&&(only_eject||!mid_once)&&edits.size()>=2){'
assert needle in s;s=s.replace(needle,'        auto accepted_before_eject=mid_accepts;\n'+needle)
needle='        post_saved += int(input_ops.size()) - int(best_ops.size());'
assert needle in s;s=s.replace(needle,'''        if(trim_after&&mid_accepts>accepted_before_eject){
            edits=anchorize(best_ops);
            for(int pass=0;pass<3;pass++)if(!delete_singles())break;
        }
'''+needle)
(p/'main.cpp').write_text(s)
