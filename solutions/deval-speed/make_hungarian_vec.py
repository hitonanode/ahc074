from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-hungarian/main.cpp').read_text()
s=s.replace('std::vector<int> hungarian(const std::vector<std::vector<double>>& cost)', '__attribute__((target("avx2"))) std::vector<int> hungarian(const std::vector<std::vector<double>>& cost)',1)
lo=s.index('            for (int j = 1; j <= n; j++)\n                if (!used[j])',s.index('std::vector<int> hungarian('))
hi=s.index('            for(int q=0;q<visited_count;',lo)
s=s[:lo]+'''            // Four independent columns; reduction ties use the lower column
            // index, exactly as the original increasing-j scalar scan.
            __m256d minima=_mm256_set1_pd(1e100);
            __m256i indices=_mm256_set1_epi64x(n+1);
            const __m256d potential=_mm256_set1_pd(u[i0]);
            int j=1;
            for(;j+3<=n;j+=4) {
                uint32_t packed;
                std::memcpy(&packed,used.data()+j,4);
                const __m256i flags=_mm256_cvtepu8_epi64(_mm_cvtsi32_si128(int(packed)));
                const __m256d live=_mm256_castsi256_pd(_mm256_cmpeq_epi64(flags,_mm256_setzero_si256()));
                const __m256d old=_mm256_loadu_pd(minv.data()+j);
                const __m256d cur=_mm256_sub_pd(_mm256_sub_pd(_mm256_loadu_pd(cost[i0-1].data()+j-1),potential),_mm256_loadu_pd(v.data()+j));
                const __m256d improve=_mm256_and_pd(live,_mm256_cmp_pd(cur,old,_CMP_LT_OQ));
                const __m256d next=_mm256_blendv_pd(old,cur,improve);
                _mm256_storeu_pd(minv.data()+j,next);
                const int mask=_mm256_movemask_pd(improve);
                if(mask&1)way[j]=j0;
                if(mask&2)way[j+1]=j0;
                if(mask&4)way[j+2]=j0;
                if(mask&8)way[j+3]=j0;
                const __m256d better=_mm256_and_pd(live,_mm256_cmp_pd(next,minima,_CMP_LT_OQ));
                minima=_mm256_blendv_pd(minima,next,better);
                indices=_mm256_blendv_epi8(indices,_mm256_setr_epi64x(j,j+1,j+2,j+3),_mm256_castpd_si256(better));
            }
            alignas(32) double values[4];alignas(32) long long at[4];
            _mm256_store_pd(values,minima);_mm256_store_si256(reinterpret_cast<__m256i*>(at),indices);
            for(int lane=0;lane<4;++lane)
                if(values[lane]<delta || (values[lane]==delta && at[lane]<j1))delta=values[lane],j1=at[lane];
            for(;j<=n;++j)if(!used[j]) {
                const double cur=cost[i0-1][j-1]-u[i0]-v[j];
                if(cur<minv[j])minv[j]=cur,way[j]=j0;
                if(minv[j]<delta)delta=minv[j],j1=j;
            }
'''+s[hi:]
d=ROOT/'solutions/deval-hungarian-vec';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-hungarian-vec

改良元: solutions/deval-hungarian（元はdeval-vbranch-o3）。

Hungarian法の距離更新を4列ずつAVX2で計算する。各列の減算順を保ち、最小値の同点では列番号が最小のものを選ぶ。訪問済み列のポテンシャル更新と未確定距離の一括減算も分離する。探索予算・浮動小数点モード・時間ガードは同じ。
''')
print(len(s.encode()))
