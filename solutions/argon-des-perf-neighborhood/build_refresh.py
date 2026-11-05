"""Separate another local pass from updating the head probabilities after perforation."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent;base=(root/'argon-des-perf-gaincache/main.cpp').read_text()
for name,rebuild in [('argon-des-perf-pass2',False),('argon-des-perf-reprob2',True)]:
    out=root/name;assert not out.exists(),name;out.mkdir()
    refresh='    perforation.rebuild();\n'if rebuild else ''
    source=base.replace('    perforation.run(0.7);', '''    perforation.run(0.7);
    const double d2_start = elapsed_sec();
    const int d2_holes = perforation.holes(), d2_accepts = perforation.accepted;
    const auto d2_old_probability = perforation.probability;
'''+refresh+'''    double d2_probability_shift = 0;
    for (int c = 0; c < perforation.H; ++c)
        d2_probability_shift += std::abs(perforation.probability[c][1] - d2_old_probability[c][1]);
    perforation.run(0.7);
    std::cerr << "d2_holes_delta = " << perforation.holes() - d2_holes
              << "\\nd2_accepts = " << perforation.accepted - d2_accepts
              << "\\nd2_probability_shift = " << d2_probability_shift
              << "\\nd2_sec = " << elapsed_sec() - d2_start << '\\n';''')
    (out/'main.cpp').write_text(source)
    (out/'README.md').write_text(f'''改良元: solutions/argon-des-perf-gaincache

穿孔後に{'更新した穴需要からhead色確率・色標本・効用・DPを再構築し、' if rebuild else '同じ確率・標本・headを使い、'}
同じ候補順でもう1周、係数0.7で穿孔・復元を試す。
{'穴が増えた後の色確率への追従を調べる。headの紙IDは固定する。' if rebuild else '再構築する案の対照として、単に2周目を足す効果を分離する。'}
追加段の受理数・穴数差・色確率の絶対差和・時間をd2_accepts/holes_delta/probability_shift/secに出す。
新しい環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
''')
    (out/'.gitignore').write_text('/__pycache__/\n')
