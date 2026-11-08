from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='__attribute__((target("avx2"))) void eject_repairs(';assert s.count(a)==1
s=s.replace(a,'__attribute__((target("avx2,bmi,popcnt"))) void eject_repairs(')
a='auto prepare_positions = [&] {';assert s.count(a)==1
s=s.replace(a,'auto prepare_positions = [&]() __attribute__((target("bmi,popcnt"))) {')
d=R/'solutions/dcomp-t11-eject-bmi';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nprofileで約16msだったejectのfirst/second窓owner列挙、および修復部のbit列挙にBMIとpopcnt命令を許可する。整数のzero-bit消去・ctzを対象にし、FMAやfast-mathは追加しない。Clang nativeでは既に同等命令が使用可能なため差が小さい対照になる。\n\n演算順・候補順・予算は変えない。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
