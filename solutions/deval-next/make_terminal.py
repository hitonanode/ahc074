from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
for horizon in [1,4,16]:
 name=f'deval-terminal{horizon}'
 s=b.replace('static constexpr double kTopPenalty = 0.00, kEndWeight = 1.0;','''static constexpr double kTopPenalty = 0.00;
    double kEndWeight = 1.0, future_discount = 1.0;
    int orders_done = 0, total_orders = 1024;''',1)
 old='''        return charge;
    }
    // Expected cost of the next request'''
 assert old in s;s=s.replace(old,'''        return future_discount * charge;
    }
    // Expected cost of the next request''',1)
 old='''    Moves process(int u) {
        CF_SCOPE(process);'''
 assert old in s;s=s.replace(old,f'''    Moves process(int u) {{
        CF_SCOPE(process);
        // Finite-order horizon, independent of elapsed time or benchmark mode.
        const int remaining = total_orders - 1 - orders_done++;
        future_discount = std::min(1., std::max(0, remaining) / {horizon}.);
        kEndWeight = future_discount;''',1)
 pos=s.rfind('    Solver solver = make_solver(state);')
 assert pos>=0;s=s[:pos]+s[pos:].replace('    Solver solver = make_solver(state);','    Solver solver = make_solver(state);\n    solver.total_orders = R;',1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
 (p/'README.md').write_text(f'改良元: `solutions/deval-seven-wide`\n\n最後の{horizon}注文で将来費用（fillerの将来返却費用と次注文の状態価値）を残り注文数/{horizon}倍にする。最終注文では0、他は上限1。探索回数と候補は同じで、時計・LOCAL_BENCHによる切り替えはない。注文カウンタは提出でも動く。設計は同一。\n')
 print(name,len(s.encode()))
