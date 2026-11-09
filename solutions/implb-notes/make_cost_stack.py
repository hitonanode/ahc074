from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
base=(root/'solutions/d30a-stack1/main.cpp').read_text()
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a),n)
 return s.replace(a,b)
def field(s,name,value):
 text=f'''#ifdef LOCAL_BENCH
    inline static const double {name} = env_real("D30B_{name.upper()}", {value});
#else
    static constexpr double {name} = {value};
#endif
'''
 return replace(s,'    static constexpr double kHoleWeight = 0.38;',text+'    static constexpr double kHoleWeight = 0.38;')
def apply_knob(s,knob,value):
 switch='なし（整数SIMDと定数畳み込みを維持）'
 if knob=='hole':
  s=replace(s,'kHoleWeight = 0.38;',f'kHoleWeight = {value};')
  s=replace(s,'// all 64 handles, the hole-cost change is below 8192 (4*kHoleWeight < 2).','// all 64 handles, the hole-cost change is at most 64*64*4*kHoleWeight.')
  s=replace(s,'            if (delta_col40 > 400000) {','            static_assert(64*64*4*kHoleWeight + 22 < 10000);\n            if (delta_col40 > 400000) {')
  why='handle-hole の修復費用の重み。複数穴をまとめて直す注文処理に対する限界費用を検査する。'
 elif knob=='column':
  s=replace(s,'least_depths2(nc, nt, p1) * 0.5',f'least_depths2(nc, nt, p1) * {value*.5:.2f}')
  s=replace(s,'20 * least_depths2(nc, nt, p1)',f'{round(20*value)} * least_depths2(nc, nt, p1)')
  s=replace(s,'_mm_mullo_epi32(minimum2, _mm_set1_epi32(20))',f'_mm_mullo_epi32(minimum2, _mm_set1_epi32({round(20*value)}))')
  why='列の最小掘り出し深さの重み。再利用・後処理によって回避できる掘りとのずれを検査する。scalar と SIMD を同じ倍率にする。'
 else:
  name={'generic':'kGenericScale','climb':'kClimbScaleValue','rematch':'kRematchScale','perfweight':'kPerfWeight','headreset':'kHeadReset','perfreset':'kPerfReset'}[knob]
  s=field(s,name,value);switch=f'D30B_{name.upper()}（既定 {value}、基準値 '+str({'generic':1.,'climb':.5,'rematch':1.,'perfweight':.7,'headreset':2.,'perfreset':2.}[knob])+'）'
  if knob=='generic':
   s=replace(s,'gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]);',f'gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]) * {name};')
   why='汎用層の単独・一様状態からの費用を倍率補正。初期化、焼きなまし、再割り当ての表を同じ倍率で変更する。pair の需要倍率 2 は維持する。'
  elif knob=='climb':
   s=replace(s,'Design::kClimbProxyWeight=.5;',f'Design::kClimbProxyWeight=Design::{name};')
   why='filler climb の代理利益の重み。reset=6 と返却費用0.8へ変わった基準で、旧最適値0.5を検査する。'
  elif knob=='rematch':
   s=replace(s,'extra?1:2, 1.0,',f'extra?1:2, 1.0 * Design::{name},')
   s=replace(s,'late_iterations, 1.25,',f'late_iterations, 1.25 * Design::{name},')
   why='ProbabilityHead の filler 利益の重み。初回1.0と穿孔後1.25の比を保って同時に倍率補正する。勾配と最終受理の両方に適用される。'
  elif knob=='perfweight':
   s=replace(s,'perforation.run(0.7);',f'perforation.run(Design::{name});')
   why='穿孔の donor 利益の受理重み。複数filler・owner補正が入った後の旧0.7を検査する。DPの返却費用は変更しない。'
  elif knob=='headreset':
   s=replace(s,'head_probability(hn[c][0], hn[c][1], 2.0 * nt[c])',f'head_probability(hn[c][0], hn[c][1], {name} * nt[c])')
   s=replace(s,'extra?1:2, 1.0, 2.0)',f'extra?1:2, 1.0, Design::{name})')
   s=replace(s,'late_iterations, 1.25, 2.0,',f'late_iterations, 1.25, Design::{name},')
   why='climb/ProbabilityHead の先頭色確率だけの reset 需要倍率。焼きなましの reset_strength=6 は維持し、確率側に残った2との不整合を検査する。'
  elif knob=='perfreset':
   s=replace(s,'2 * demands[c]',f'Design::{name} * demands[c]',2)
   why='穿孔の色確率と追加穴費用に残った reset 需要倍率。両方を同時に変え、焼きなましの reset_strength=6 は維持する。'
 return s,why,switch

if __name__ == '__main__':
 import sys
 name=sys.argv[1];items=[(x.split('=')[0],float(x.split('=')[1])) for x in sys.argv[2:]]
 assert name.startswith('d30b-')
 assert len(set(k for k,v in items))==len(items)
 items.sort(key=lambda x: -1 if x[0]=='headreset' else 1 if x[0]=='hole' else 0)
 source=base;notes=[]
 for knob,value in items:
  source,why,switch=apply_knob(source,knob,value)
  notes.append(f'- {knob}={value}: {why} 環境変数: {switch}')
 path=root/'solutions'/name;path.mkdir(exist_ok=False)
 (path/'main.cpp').write_text(source)
 (path/'README.md').write_text('改良元: solutions/d30a-stack1\n\n設計モデル定数のscreenで選んだ変更を重ねる。\n\n'+'\n'.join(notes)+'\n\n固定反復回数、CLOCK_SCALE、DesignStore、既存ログを維持する。reset_strength、covered_gainの返却費用、fret-full、V回帰係数は変更しない。追加stderr指標なし。\n')
 print(path)
