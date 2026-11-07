from pathlib import Path
R=Path(__file__).resolve().parents[2]
base=(R/'solutions/deval-refinish-fast/main.cpp').read_text()
for name,extras,climb in [('deval-refinish8f',4,25000),('deval-refinish10f',6,12000),('deval-refinish12f',8,6000)]:
 s=base.replace('for(int j=0;j<4;++j)',f'for(int j=0;j<{extras};++j)',1).replace('extra?25000:climb_iters',f'extra?{climb}:climb_iters',1)
 needle='        return std::getenv(local.c_str());'
 assert s.count(needle)==1
 s=s.replace(needle,'''        if(const char* value=std::getenv(local.c_str()))return value;
        if(std::strcmp(name,"REPEAT_MIN")==0)return ".05";
        if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";
        return nullptr;''',1)
 needle='begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;'
 s=s.replace(needle,needle+'\n        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr<<"@deval_final "<<id<<\' \'<<v<<\'\\n\';',1)
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-refinish-fast。

元の4候補をclimb50k・再割当て2回・穴あけ8サンプル・最終再割当てまで完成させ、すべて残す。完成Vの上位2候補の対象・列の配置から、固定saltを変えて計{extras}回、独立にclimb{climb}回・再割当て1回・穴あけ8サンプル・最終再割当てを行う。物理的な穴は作り直す。全{4+extras}完成候補から最小Vを選ぶ。

注文探索の固定設定をREPEAT_MIN=0.05、POST_CANDIDATES=5にする。小さい改善後の再探索を省き、その分で後処理の候補を広く見る。環境変数F3_*で実験時に上書きできるが、時間に応じた予算変更はない。

高速化はdeval-climbcacheと同じ。窓・焼きなましの反復数は元と同じ。時間不足の切替えはない。DesignStore、ログ、@paper/@ops、目次・段の目印を維持。
''')
 print(name,len(s.encode()))
