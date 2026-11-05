"""Reuse Hungarian's exact acceptance for whole-unit moves across columns."""
from pathlib import Path

base=Path('solutions/argon-des-perf-rematch-v2')
s=(base/'main.cpp').read_text()
def change(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)

change('''                               const std::vector<u64>* extra = nullptr) {
    AF_SCOPE(rematch, 1);''','''                               const std::vector<u64>* extra = nullptr, bool whole_units = false) {
    AF_SCOPE(rematch, 1);''')
change('''                if (rng() & 1) std::swap(anchor[x], mobile[x]);''',
       '''                if (!whole_units && (rng() & 1)) std::swap(anchor[x], mobile[x]);''')
change('''            int c = d.unit[i].c, a = anchor[i];
            for (int j = 0; j < d.U; j++) {
                int b = mobile[j];
                if (int(d.hb[b] >> c & 1) != color[i] || (a >= 0 && !d.ok[a][b])) continue;''',
       '''            int c = d.unit[i].c;
            for (int j = 0; j < d.U; j++) {
                const int a = whole_units ? anchor[j] : anchor[i], b = mobile[j];
                // Whole-unit cycles keep each physical slot's frequency and own-handle color.
                if (whole_units && ((a < 0) != (anchor[i] < 0))) continue;
                if (int(d.hb[b] >> c & 1) != color[i] ||
                    (a >= 0 && (!d.ok[a][b] || int(d.hb[a] >> c & 1) != color[i]))) continue;''')
change('''                d.unit[x].b = anchor[x];''',
       '''                d.unit[x].b = anchor[whole_units ? assigned[x] : x];''')
needle='''        const auto late = rematch_probability(*des, late_iterations, 1.0, 2.0, &extra);
        int remaining = 0;'''
change(needle,'''        const auto late = rematch_probability(*des, late_iterations, 1.0, 2.0, &extra);
        // Move complete singles/pairs among fixed physical paper slots. Extra holes
        // belong to the slots, so their effect is reevaluated for the incoming targets.
        const auto whole = rematch_probability(*des, 1, WHOLE_WEIGHT, 2.0, WHOLE_EXTRA, true);
        std::cerr << "d2_whole_cycles = " << whole.accepted_cycles
                  << "\\nd2_whole_changed = " << whole.changed
                  << "\\nd2_whole_decrease = " << whole.decrease
                  << "\\nd2_whole_model_initial = " << whole.initial_model
                  << "\\nd2_whole_model_final = " << whole.final_model
                  << "\\nd2_whole_filler_initial = " << whole.initial_filler
                  << "\\nd2_whole_filler_final = " << whole.final_filler
                  << "\\nd2_whole_sec = " << whole.seconds << '\\n';
        int remaining = 0;''')

for name,w,extra in [('whole',1.0,'&extra'),('wholeplain',1.0,'nullptr'),('wholehalf',.5,'&extra')]:
    dst=Path('solutions/argon-des-perf-'+name)
    assert not dst.exists()
    dst.mkdir()
    (dst/'main.cpp').write_text(s.replace('WHOLE_WEIGHT',str(w)).replace('WHOLE_EXTRA',extra))
    (dst/'README.md').write_text(f'''改良元: solutions/argon-des-perf-rematch-v2

穿孔後再割当の後、単独紙・ペア紙の所有目標全体を、同じ頻度・自身のハンドル色の紙位置へ
移すHungarianを1回追加する。列・紙位置の追加穴は固定し、ペアは分割しない。
filler climbと同様の列交換を、多点cycleと現在の模様の目的関数で調べる。
フィラー係数は{w}。追加穴の評価は{'含める' if extra=='&extra' else '対照として無視するが、印刷では保持する'}。
元の全ログ・スイッチ・プロファイラ・DesignStore・段の目印を保持する。
d2_whole_*は受理cycle数・移動unit数・予測改善・費用とフィラー価値の開始/終了値・時間。
d2_rematch_secは追加全体の時間になり、d2_whole_secはその内訳。
''')
    print(dst)
