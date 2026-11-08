from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
x='''        std::vector<ColRow> rows;''';assert B.count(x)==1
s=B.replace(x,'''        // n0,n1 are exact target counts, and reset is twice an integer target count.
        // Tables are shared across segments and branches of this case; untouched resets
        // allocate no entries. The quotient is rounded by the original qf expression.
        inline static std::vector<float> hole_quotients;
        inline static std::array<int,P+1> hole_offsets=[] {
            std::array<int,P+1> a;a.fill(-1);return a;
        }();
        alignas(32) std::array<int,L> hole_base{};
        const float* quotient_data=nullptr;
        void init_hole_quotients() {
            constexpr int side=P+1,area=side*side;
            if(hole_quotients.capacity()==0)hole_quotients.reserve(size_t(side)*area);
            for(int j=0;j<L;++j) {
                const int r=j<H?int(D.reset_targets[j]/2):0;
                assert(r>=0 && r<=P);
                if(hole_offsets[r]<0) {
                    const int base=hole_quotients.size();hole_offsets[r]=base;
                    hole_quotients.resize(base+area);
                    for(int a=0;a<=P;++a)for(int b=0;b<=P;++b)
                        hole_quotients[base+a*side+b]=qf(float(a),float(b),float(2*r));
                }
                hole_base[j]=hole_offsets[r];
            }
            quotient_data=hole_quotients.data();
        }
'''+x)
x='''            cur = D.cur;
        }

        // Units x, y moved''';assert s.count(x)==1
s=s.replace(x,'''            init_hole_quotients();
            cur = D.cur;
        }

        // Units x, y moved''')
x='''                Q[r] = _mm256_div_ps(numerator, s);''';assert s.count(x)==1
s=s.replace(x,'''                const auto qa=_mm256_cvttps_epi32(N0[r]),qb=_mm256_cvttps_epi32(N1[r]);
                const auto index=_mm256_add_epi32(_mm256_load_si256((const __m256i*)(hole_base.data()+8*r)),
                    _mm256_add_epi32(_mm256_mullo_epi32(qa,_mm256_set1_epi32(P+1)),qb));
                Q[r]=_mm256_i32gather_ps(quotient_data,index,4);
#ifdef HOLE_QUOTIENT_CHECK
                const auto reference=_mm256_div_ps(numerator,s);
                if(_mm256_movemask_epi8(_mm256_cmpeq_epi32(_mm256_castps_si256(Q[r]),_mm256_castps_si256(reference)))!=-1)
                    {std::cerr<<"HOLE_QUOTIENT_MISMATCH\\n";std::abort();}
#endif''')
for name,src,desc in [('dcomp-t11-holetable',s,''),('dcomp-t11-holecheck','#define HOLE_QUOTIENT_CHECK 1\n'+s,'全laneを元のSIMD除算とbit照合する検証版。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(src)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nannealのeval_holesが約150msを占めるため、整数カウントの正確なqf商を表にする。resetは2×整数なのでresetごとに257×257個を元のqfで生成し、全segment・branchで共有する。SIMD除算をAVX2 gatherで置換する。加算順と最終sumはそのまま。'+desc+'\n\n表は使ったresetだけ生成する。最大仮想reserveは約68MB、実際に生成した部分だけ使用。近似・fast-math・時計による切替は使わず、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
