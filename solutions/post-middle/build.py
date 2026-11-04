from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'perforated-eight/main.cpp').read_text()
s=s.replace('static inline int post_rewrite_mode=5;', 'static inline int mid_eject_mode=2;\n    long long mid_pairs=0,mid_trials=0,mid_accepts=0,mid_inside=0;\n    static inline int post_rewrite_mode=5;')
anchor='        post_saved += int(input_ops.size()) - int(best_ops.size());'
assert s.count(anchor)==1
s=s.replace(anchor,(p/'eject.inc').read_text()+'\n'+anchor)
(p/'main.cpp').write_text(s)
