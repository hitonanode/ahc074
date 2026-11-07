"""Exact integer-domain qf table shared by anneal segments and branches."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
s=base
needle='    template <int NR>\n    struct Annealer {'
pos=s.index(needle)
code='''    // The counts and reset=2*nt are exact integers. Populate each needed
    // reset slice once, with the same numerator and correctly rounded float
    // division as the SIMD kernel. Unused slices allocate no physical pages.
    ANNEAL_TARGET static const float* anneal_q_table(int nt) {
        static std::unique_ptr<float[]> table(new float[257*257*257]);
        static std::array<bool,257> ready{};
        assert(nt>=0&&nt<=256);
        if(!ready[nt]) {
            ready[nt]=true;
            float* dst=table.get()+nt*257*257;
            const __m256 half=_mm256_set1_ps(float(nt)),reset=_mm256_set1_ps(float(2*nt));
            const __m256 one=_mm256_set1_ps(1.f);
            for(int a=0;a<=256;++a) {
                const auto aa=_mm256_set1_ps(float(a));
                for(int b=0;b<256;b+=8) {
                    const auto bb=_mm256_setr_ps(float(b),float(b+1),float(b+2),float(b+3),float(b+4),float(b+5),float(b+6),float(b+7));
                    const auto num=_mm256_fmadd_ps(half,_mm256_min_ps(aa,bb),_mm256_mul_ps(aa,bb));
                    const auto den=_mm256_max_ps(_mm256_add_ps(_mm256_add_ps(aa,bb),reset),one);
                    _mm256_storeu_ps(dst+a*257+b,_mm256_div_ps(num,den));
                }
                dst[a*257+256]=(float(a)*256.f+float(nt)*float(a))/std::max(1.f,float(a+256+2*nt));
            }
        }
        return table.get();
    }
'''
s=s[:pos]+code+s[pos:]
s=s.replace('        std::vector<ColRow> rows;','        std::vector<ColRow> rows;\n        const float* qlookup=nullptr;\n        alignas(32) int qoffset[L]{};',1)
s=s.replace('            for (int j = 0; j < H; j++) {\n                reset[j] = D.reset_targets[j];','''            qlookup=anneal_q_table(0);
            for (int j = 0; j < H; j++) {
                reset[j] = D.reset_targets[j];
                const int nt=int(reset[j])/2;
                assert(reset[j]==2.f*nt);
                anneal_q_table(nt);
                qoffset[j]=nt*257*257;''',1)
start=s.index('                const __m256 reset_count =',s.index('float eval_holes('))
end=s.index('                dif[r] =',start)
s=s[:start]+'''                const auto a=_mm256_cvttps_epi32(N0[r]),b=_mm256_cvttps_epi32(N1[r]);
                const auto index=_mm256_add_epi32(_mm256_load_si256(reinterpret_cast<const __m256i*>(qoffset+8*r)),
                    _mm256_add_epi32(_mm256_mullo_epi32(a,_mm256_set1_epi32(257)),b));
                Q[r]=_mm256_i32gather_ps(qlookup,index,4);
'''+s[end:]
def save(name,source,desc):
    d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(source)
    (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{desc}\n候補・乱数・浮動小数点の演算結果と時間ガードを保つ。\n')
    print(name,len(source.encode()))
save('deval-qtable',s,'焼きなましの穴数は整数、resetは2×整数なので、qfの正確なfloat値を表にする。必要になったresetだけを同じSIMD除算で一度生成し、後の段・分岐でも共有する。既存のAVX2で8項を参照する。最大約68MBの未初期化領域を確保し、実際に使うresetのページだけに書く。')
save('deval-dirtyall',base.replace('if (r == NR - 1 && !((dirty >> (8 * r)) & 255)) {','if (!((dirty >> (8 * r)) & 255)) {',1),'穴数が変わらないSIMD群を、最終群だけでなく全群で省く。変更0の差分は元と同じ+0。')
save('deval-dirtyfirst',base.replace('if (r == NR - 1 && !((dirty >> (8 * r)) & 255)) {','if ((r == 0 || r == NR - 1) && !((dirty >> (8 * r)) & 255)) {',1),'穴数が変わらない最初と最後のSIMD群を省く。中央の群には分岐を加えない。')
