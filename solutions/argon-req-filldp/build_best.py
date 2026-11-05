from pathlib import Path
import sys,subprocess
name=sys.argv[1];mode=sys.argv[2] if len(sys.argv)>2 else '3'
subprocess.run([sys.executable,'solutions/argon-req-filldp/build.py',name,mode],check=True)
p=Path('solutions')/name
s=p.joinpath('main.cpp').read_text()
s=s.replace(f'''        const auto original_opts = opts;
        for (auto o : original_opts) {{ o.r2_mode = {mode}; opts.push_back(o); }}
''','',1)
s=s.replace('''        tail_cache_on = false;
        r2_mode = 0;''',f'''        if (best_normal < 1e17) {{
            start_plan(st0);
            auto alternative = best_normal_opt;
            alternative.r2_mode = {mode};
            ++r2_alt_trials;
            run_plan(u, alternative);
            if (!invalid && ops.size() <= 2 * K && display() == A[u] && fillers_reachable()) {{
                ++r2_alt_valid;
                r2_alt_novel += std::find(r2_orders.begin(), r2_orders.end(), order) == r2_orders.end();
                const double cost = plan_cost(ops.size());
                if (cost < r2_baseline_best - 1e-9) ++r2_raw_better, r2_raw_gain += r2_baseline_best - cost;
                record_future(cost);
                if (cost < best) best = cost, best_ops = ops OP_TAG(, best_tags = op_tags), best_state = save();
            }}
        }}
        tail_cache_on = false;
        r2_mode = 0;''',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+'''
追加計画は、後処理前に最良だった通常計画（共同DPを除く）の返却方法だけで試す。重み以外の既存計画は全て維持する。
''')
