from pathlib import Path
p=Path('solutions/argon-req-k2late-profile'); assert not p.exists(); p.mkdir()
s=Path('solutions/argon-req-k2late-fast/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80]); s=s.replace(a,b,1)
sub('''    inline static long long joint_late_trials''','''    struct JointLateProfile { long long trials, ejects, accepts, saved; double gain, edit_sec, eject_sec; };
    inline static std::array<JointLateProfile,64> joint_late_profile{};
    inline static long long joint_late_trials''')
sub('''        ++joint_late_trials;
        const auto incumbent = save();''','''        ++joint_late_trials;
        const double edit_start = elapsed_sec();
        const auto incumbent = save();''')
sub('''        double next = plan_cost(path.size());
        if (next <= value + .5 && order != incumbent.order) {''','''        double next = plan_cost(path.size());
        const double gap = next-value;
        const int band = gap <= 0 ? 0 : gap <= .25 ? 1 : gap <= .5 ? 2 : 3;
        std::array<bool,K> moved{}, seen{};
        for (auto [k,d] : chosen) moved[k]=true;
        bool repeated=false, added=false;
        for (auto [k,d] : path) { repeated |= seen[k]; seen[k]=true; added |= !moved[k]; }
        const int delta=int(path.size())-int(chosen.size());
        const int length=delta<0 ? 0 : delta==0 ? 1 : delta==1 ? 2 : 3;
        auto& profile = joint_late_profile[band + 4*repeated + 8*added + 16*length];
        ++profile.trials;
        profile.edit_sec += elapsed_sec()-edit_start;
        const double eject_start = elapsed_sec();
        if (next <= value + .5 && order != incumbent.order) {
            ++profile.ejects;''')
sub('''        if (next < value - 1e-9 && display() == A[u] && fillers_reachable()) {
            ++joint_late_accepts;''','''        profile.eject_sec += elapsed_sec()-eject_start;
        if (next < value - 1e-9 && display() == A[u] && fillers_reachable()) {
            ++profile.accepts;
            profile.gain += value-next;
            profile.saved += int(chosen.size())-int(path.size());
            ++joint_late_accepts;''')
sub('    // ==== main: statistics ====\n','''    // ==== main: statistics ====
    for (int i=0; i<64; ++i) {
        const auto& q = solver.joint_late_profile[i];
        const std::string prefix = "joint_profile_" + std::to_string(i) + '_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "ejects = " << q.ejects << '\\n'
                  << prefix << "accepts = " << q.accepts << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "saved = " << q.saved << '\\n'
                  << prefix << "edit_sec = " << q.edit_sec << '\\n'
                  << prefix << "eject_sec = " << q.eject_sec << '\\n';
    }
''')
(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

solutions/argon-req-k2late-fast と同じ第2解の独立処理を行い、安い編集後の特徴別に費用と採用利得を測る。探索の候補・順序・採用条件は変えない。

joint_profile_<i>_* のiは band + 4*repeated + 8*added + 16*length。bandは編集後評価値差が0以下/.25以下/.5以下/それ以上、repeatedは同じ紙の複数回移動、addedは基準最終経路にない紙の移動の有無、lengthは基準より短い/同じ/1手長い/2手以上長い。trials/ejects/accepts/gain/saved/edit_sec/eject_secは試行・eject・採用数、完成評価改善、即時手数差、編集・eject時間。既存ログ・スイッチ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・節と目次を保持する。
''')
print(p)
