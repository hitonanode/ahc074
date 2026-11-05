"""Measurement builds: residual sampling variance at the new coefficient."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
base=(root/'argon-des-perf-gaincache/main.cpp').read_text()
for name,weight in [('argon-des-perf-dense70',.7),('argon-des-perf-dense80',.8)]:
    out=root/name
    assert not out.exists(),name
    source=base.replace('kSamples = 8;','kSamples = 512;')
    source=source.replace('    perforation.run(0.7);',f'''    const double d2_old_cost = perforation.hole_cost;
    const double d2_old_profit = perforation.profit;
    perforation.run({weight});
    std::cerr << "d2_cost_delta = " << (perforation.hole_cost - d2_old_cost) / P
              << "\\nd2_profit_delta = " << (perforation.profit - d2_old_profit) / P
              << "\\nd2_prediction = " << (perforation.hole_cost - d2_old_cost - {weight} *
                    (perforation.accepted_owner_corrected + perforation.accepted_donor)) / P << '\\n';''')
    out.mkdir();(out/'main.cpp').write_text(source)
    (out/'README.md').write_text(f'''改良元: solutions/argon-des-perf-gaincache

測定専用。色標本を512個に増やし、係数{weight}で穿孔する。
owner側の条件付け、上限、差分キャッシュは基準と同じ。
現在の係数の下で標本誤差を減らした時の到達点を見る。真の最適設計を返すオラクルではない。
時間超過の可能性が高いため、通常評価でも --no-record を使う。

d2_cost_delta/profit_deltaは穴費用と未補正利益の変化（手/注文）。
d2_predictionは受理係数とowner補正を含む予測変化。
追加の環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
''')
    (out/'.gitignore').write_text('/__pycache__/\n')
