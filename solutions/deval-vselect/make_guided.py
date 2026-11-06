"""Use the cheap completion predictor to restart anneal segments from elites."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vguided'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
src=src.replace('env_real("DEVAL_MODE",1)','env_real("DEVAL_MODE",4)')
src=src.replace('env_int("DEVAL_CANDIDATES"):4','env_int("DEVAL_CANDIDATES"):3')
src=src.replace('std::clamp(int(env_real("DEVAL_ELITES",8)),1,64)',
                'std::clamp(int(env_real("DEVAL_ELITES",32)),1,64)')
lo=src.index('    } else if(mode==4) {')
hi=src.index('    } else if(mode) {',lo)
part=src[lo:hi]
part=part.replace('            begin=elapsed_sec();\n            int selected=',
    '            if(segment==3)break; // the final pool is finished and selected below\n            begin=elapsed_sec();\n            int selected=')
part=part.replace('const double v=value.from_design(raw);','const double v=prescreen_value(raw,value);')
src=src[:lo]+part+src[hi:]
src=src.replace('mode==3||mode==5','mode==3||mode==4||mode==5')
assert len(src.encode())<=520000
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vguided

改良元: `solutions/deval-vclean`。

前半 2 段は元の焼きなまし。第 3 段の現在状態を 32 個保存し、仕上げ後の V を予測する軽いモデルで最良の状態を選んで、第 4 段を始める。第 4 段でも 32 個の状態を保存し、同モデルの上位 3 個を仕上げて V16 で選ぶ。総焼きなまし反復数は SOTA と同じ。予測に注文処理を使わない。

仕上げは filler climb 50,000 回、再割当て 2 回、穴あけと最終再割当て。時間ガード、DesignStore、診断は親と同じ。生成は `solutions/deval-vselect/make_guided.py`。
''')
print('source bytes',len(src.encode()))
