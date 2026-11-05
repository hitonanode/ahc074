from pathlib import Path
import sys,subprocess
name=sys.argv[1]
subprocess.run([sys.executable,'solutions/argon-req-filldp/build.py',name,'4'],check=True)
p=Path('solutions')/name
s=p.joinpath('main.cpp').read_text()
s=s.replace('    int r2_mode = 0;\n    long long', '''    int r2_mode = 0;
    bool r2_dp_ready = false, r2_prelift = false;
    int r2_u = -1, r2_d = -1;
    u64 r2_holes = 0;
    double r2_reference = 0;
    // Complete a singleton interval to value the digs it avoids, including their
    // effects on the other columns. This is a measurement-only, expensive oracle.
    double r2_completed(int c, int depth, int level) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        invalid = false;
        u64 hh = r2_holes;
        bool post = false;
        if (c >= 0 && r2_prelift) {
            std::vector<int> top;
            column_tops(c, depth + 1, top);
            const int l = col_of[r2_d];
            post = c > l && level <= l && (paper[top[depth]].opaque >> handle[l] & 1);
        }
        if (c >= 0 && !post) place_filler(c, depth, level, hh);
        if (r2_prelift) lift(r2_d);
        if (c >= 0 && post) place_filler(c, depth, level, hh);
        fix_handles(r2_u, hh);
        const double value = invalid || display() != A[r2_u] ? 1e30 : plan_cost(ops.size());
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return value;
    }
    void r2_prepare(int u, int d, u64 hh, bool prelift) {
        r2_dp_ready = r2_mode == 4;
        if (!r2_dp_ready) return;
        r2_u = u; r2_d = d; r2_holes = hh; r2_prelift = prelift;
        r2_reference = r2_completed(-1, 0, 0);
    }
    long long''',1)
s=s.replace('''        if (!r2_mode || gain < 0) return gain;
        ++r2_intervals;''','''        if (!r2_mode || gain < 0) return gain;
        ++r2_intervals;''',1)
s=s.replace('''        if (r2_mode == 1) return gain + 1e-5;''','''        if (r2_mode == 1) return gain + 1e-5;
        if (r2_mode == 4 && r2_dp_ready) {
            const double value = r2_reference - r2_completed(c, depth, level);
            r2_zero_profitable += gain == 0 && value > 1e-9;
            return value;
        }''',1)
s=s.replace('''    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) {
        auto fix''','''    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) {
        r2_prepare(u, d, hh, false);
        auto fix''',1)
s=s.replace('''        CF_SCOPE(choose_fillers);
        placement_chains.clear();''','''        CF_SCOPE(choose_fillers);
        r2_prepare(u, d, hh, true);
        placement_chains.clear();''',1)
s=s.replace('''        CF_SCOPE(run_joint);
        int d''','''        CF_SCOPE(run_joint);
        r2_dp_ready = false;
        int d''',1)
p.joinpath('main.cpp').write_text(s)
p.joinpath('README.md').write_text(p.joinpath('README.md').read_text()+'''
通常のDPでは、フィラー無しでハンドルを全て直した完成状態と、候補1枚を入れて残りを直した完成状態のplan_cost差を区間の重みにする。共同DPは旧フィラーの選択と絡むため、モード3の局所抽出価値を使う。測定費用を含むため通常評価では--no-recordの対象。設計固定比較で探索の余地を測る。
''')
