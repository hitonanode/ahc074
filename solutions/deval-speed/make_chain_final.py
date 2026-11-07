from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-chain8/main.cpp').read_text()
a=s.index('    struct Branch { double value=1e100;int id=0;std::unique_ptr<Design> raw; };')
b=s.index('    std::unique_ptr<Design> best_assignment;',a)
s=s[:a]+s[b:]
a=s.index('        branches.push_back(');b=s.index('    for(int j=0;j<4;++j)',a)
s=s[:a]+'''        complete(i,0);
    }
    // Repeat the full native finishing from the best completed assignment.
    // The original four candidates remain eligible throughout the search.
'''+s[b:]
s=s.replace('const int origin=j%std::min(2,int(branches.size())),repeat=1+j/2,id=candidates+j;', 'const int repeat=1+j/2,id=candidates+j;',1)
needle='        return std::getenv(local.c_str());'
s=s.replace(needle,'''        if(const char* value=std::getenv(local.c_str()))return value;
        if(std::strcmp(name,"REPEAT_MIN")==0)return ".05";
        if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";
        return nullptr;''',1)
needle='begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;'
s=s.replace(needle,needle+'\n        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr<<"@deval_final "<<id<<\' \'<<v<<\'\\n\';',1)
for name,o3 in [('deval-chain-finish',False),('deval-chain-finish-o3',True)]:
 t=s
 if o3:
  a='// ==== Solver: papers, handles and the generic look-ahead ===='
  b='// ==== Emergency design ===='
  t=t.replace(a,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC push_options\n#pragma GCC optimize("O3")\n#endif\n'+a,1)
  t=t.replace(b,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC pop_options\n#endif\n'+b,1)
 d=R/'solutions'/name;d.mkdir(exist_ok=True);(d/'main.cpp').write_text(t)
 (d/'README.md').write_text(f'''# {name}

改良元: solutions/deval-chain8（元の設計・注文処理はdeval-vbranch-nofb）。

焼きなまし前半2段を共有した4分岐を、元と同じclimb50k・再割当て2回を使い、穴あけを32から8サンプルへ減らして最終再割当てまで完成させ、V16で比較する。その後は、現在最良の完成配置からclimb25k・再割当て1回・穴あけ・最終再割当ての一式を4回試す。各回は固定saltで乱数を変え、完成Vが良ければ次の開始配置も更新する。元の4候補を含め、計8完成候補から選ぶ。物理的な追加穴は次の仕上げで作り直す。

窓割当て450k、窓climb133k、焼きなまし総反復数約11.2M、V16の係数は元と同じ。HungarianのAVX2化、穴あけDPの整数化と差分更新、filler列の内部保持、列の連続区間走査、仕上げの確率・被覆情報の共有を使う。使われない分岐のコピーを省く。

注文探索の固定設定はREPEAT_MIN=0.05、POST_CANDIDATES=5。小さい改善後の再探索を省き、後処理で比較する候補を増やす。実験時はF3_*で上書きできる。{'GCCでは注文処理もO3でコンパイルし、fast-mathは使わない。Clangは既定の最適化設定を使う。' if o3 else 'コンパイラの浮動小数点の既定の規則を維持する。'}

時間不足による軽量化・設計打切り・候補打切りはない。固定seedと固定予算で動く。DesignStoreは選ばれた完成設計を保存する。ログ、@paper/@ops、目次と段の目印を維持する。dv_candidatesは完成数、dv_chosenは採用候補番号、dv_*_secは全候補を合計した段別時間。
''')
 print(name,len(t.encode()))
