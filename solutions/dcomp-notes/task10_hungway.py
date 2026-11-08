from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
for mode in ['mask','blend']:
 s=base
 a='''                const int mask=_mm256_movemask_pd(improve);
                if(mask&1)way[j]=j0;
                if(mask&2)way[j+1]=j0;
                if(mask&4)way[j+2]=j0;
                if(mask&8)way[j+3]=j0;'''
 b='''                const __m128i update=_mm_castps_si128(_mm_shuffle_ps(
                    _mm256_castps256_ps128(_mm256_castpd_ps(improve)),
                    _mm256_extractf128_ps(_mm256_castpd_ps(improve),1),_MM_SHUFFLE(2,0,2,0)));
'''
 if mode=='mask':b+='                _mm_maskstore_epi32(way.data()+j,update,_mm_set1_epi32(j0));'
 else:b+='''                _mm_storeu_si128((__m128i*)(way.data()+j),_mm_blendv_epi8(
                    _mm_loadu_si128((const __m128i*)(way.data()+j)),_mm_set1_epi32(j0),update));'''
 assert s.count(a)==1;s=s.replace(a,b)
 p=r/'solutions'/('dcomp-hungway-'+mode);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\nHungarianで4列分の前駆wayを更新する4つの条件分岐を、同じimprove maskの'+('masked store' if mode=='mask' else 'blend/store')+'に置き換える。slack・potential・同点処理・浮動小数点は変更しない。固定予算、ログ・実験スイッチ・DesignStoreを維持、fallbackなし。\n')
