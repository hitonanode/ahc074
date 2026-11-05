from pathlib import Path
base=Path('solutions/time-alloc/main.cpp').read_text()
variants={
 'no-eject': [('for (int round = 0; round < 4; round++) {','for (int round = 0; round < 0; round++) {')],
 'no-reedit': [('return s ? std::atoi(s) : 2;','return s ? std::atoi(s) : 1;')],
 'no-expanded': [('get("POST_CANDIDATES", mode == 2 ? 8 : mode == 1 ? 3 : 2)','get("POST_CANDIDATES", 2)')],
 'no-chains': [('if (best_normal < 1e17) {','if (false && best_normal < 1e17) {')],
 'no-memory': [('std::getenv("QM_MODE") ? env_int("QM_MODE") : 3','std::getenv("QM_MODE") ? env_int("QM_MODE") : 0')],
 'no-stay': [('if (prev_ok)\n            for (int fm : fms) opts.push_back({4, fm, true});','if (false && prev_ok)\n            for (int fm : fms) opts.push_back({4, fm, true});')],
 'no-joint': [('if (d != top0)\n            for (int rm = 1; rm <= 2; rm++) opts.push_back({rm, 5, true});','if (false && d != top0)\n            for (int rm = 1; rm <= 2; rm++) opts.push_back({rm, 5, true});')],
}
for name,subs in variants.items():
 p=Path('solutions/clean-req-'+name);assert not p.exists(),p;p.mkdir()
 s=base
 for old,new in subs:
  assert s.count(old)==1,(name,old,s.count(old));s=s.replace(old,new)
 p.joinpath('main.cpp').write_text(s)
 p.joinpath('README.md').write_text('改良元: solutions/time-alloc\n\n注文処理の単独ablation: '+name+'。既定経路だけを無効化して、固定設計で寄与と時間を測る比較用の版。\n既存のログ・指標・プロファイラ・環境変数を保持する。評価時に基準にも届く環境変数は設定しない。スコアとreq_sec、self_wrong、op_label_errorsを比較する。結果はsolutions/clean-req/REPORT.md。\n')
 print(name)
