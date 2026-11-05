"""Port to PR144 and separate hole-aware accounting from one more Hungarian round."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
old = (root/'argon-req-filterblocks-v2/main.cpp').read_text()
base = (root/'argon-req-ejectstats-v2/main.cpp').read_text()
candidate = (root/'argon-des-perf-rematch/main.cpp').read_text()

def section(s, first, last):
    return s[s.index(first):s.index(last)]

source = base
for first, last in [('struct MatchStats {', '// ==== Helper tables:'),
                    ('    // ==== design_papers: handle perforation ====', '// ==== Saving and loading the design state')]:
    oldsection = section(old, first, last)
    assert source.count(oldsection) == 1
    source = source.replace(oldsection, section(candidate, first, last))
old_toc = '//   design_papers: handle perforation\n'
assert source.count(old_toc) == 1
source = source.replace(old_toc, old_toc+'//   design_papers: perforation-aware reassignment\n')

# Keep the accepted state's model and filler terms. A rejected final cycle need not
# rebuild head tables merely to print these diagnostics.
needle = '    double decrease = 0, seconds = 0;'
assert source.count(needle) == 1
source = source.replace(needle, needle+'''
    double initial_model = 0, final_model = 0, initial_filler = 0, final_filler = 0;''')
needle = '    double initial = head.model_cost() - weight * head.last_value, merit = initial;'
assert source.count(needle) == 1
source = source.replace(needle, needle+'''
    stats.initial_model = stats.final_model = head.model_cost() / P;
    stats.initial_filler = stats.final_filler = head.last_value / P;''')
needle = '''                merit = next;
                stats.accepted_cycles++;'''
assert source.count(needle) == 1
source = source.replace(needle, '''                merit = next;
                stats.final_model = head.model_cost() / P;
                stats.final_filler = head.last_value / P;
                stats.accepted_cycles++;''')
needle = '''                  << "\\nd2_rematch_decrease = " << late.decrease'''
assert source.count(needle) == 1
source = source.replace(needle, needle+'''
                  << "\\nd2_model_initial = " << late.initial_model
                  << "\\nd2_model_final = " << late.final_model
                  << "\\nd2_filler_initial = " << late.initial_filler
                  << "\\nd2_filler_final = " << late.final_filler''')

out = root/'argon-des-perf-rematch-v2'
out.mkdir()
(out/'main.cpp').write_text(source)
readme = (root/'argon-des-perf-rematch/README.md').read_text().replace(
    '改良元: solutions/argon-req-filterblocks-v2', '改良元: solutions/argon-req-ejectstats-v2')
(out/'README.md').write_text(readme+'''\n追加段のモデル費用とフィラーproxyの開始・終了値をd2_model_initial/final、
d2_filler_initial/finalで出力する。受理済み状態の値を保存するので、表示のための再構築は行わない。
''')

out = root/'argon-des-perf-rematch-plain'
out.mkdir()
needle = 'rematch_probability(*des, late_iterations, 1.0, 2.0, &extra)'
assert source.count(needle) == 1
(out/'main.cpp').write_text(source.replace(needle, 'rematch_probability(*des, late_iterations, 1.0, 2.0)'))
(out/'README.md').write_text('''改良元: solutions/argon-des-perf-rematch-v2

追加再割当のアブレーション。追加の穴は紙に残すが、Hungarianの目的関数は
穿孔前と同じ模様・色確率・穴費用で評価する。
穿孔後の模様を使う効果と、単に探索を1回増やす効果を分離する。
その他のスイッチ、指標、ログ、プロファイラ、DesignStore、段と目次は改良元と同じ。
''')

out = root/'argon-des-perf-match5'
out.mkdir()
assert base.count('kMatchIterations = 4;') == 1
(out/'main.cpp').write_text(base.replace('kMatchIterations = 4;', 'kMatchIterations = 5;'))
(out/'README.md').write_text('''改良元: solutions/argon-req-ejectstats-v2

既存の穿孔前Hungarianを4回から5回へ増やす。新しい段・モデルは追加しない。
穿孔後の再割当と同程度の時間を、元の段へ加える対照。
それ以外のコード、スイッチ、指標、ログ、プロファイラ、DesignStore、段と目次は基準と同じ。
''')
