from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
s=B
x='    std::array<NextPaper, K> next_paper;';assert s.count(x)==1
s=s.replace(x,x+'\n    std::array<int,K> next_packed;')
x='            next_paper[k] = {uint16_t(k * stride), uint8_t(column_color[k]), uint8_t(colmdp_type[k])};';assert s.count(x)==1
s=s.replace(x,x+'\n            next_packed[k]=int(uint32_t(uint16_t(k*stride)) | (uint32_t(uint8_t(column_color[k]))<<16) | (uint32_t(uint8_t(colmdp_type[k]))<<24));')
x='''                do {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0)first[np.color]=depth;
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                } while(i<end && (next_paper[key[i]].color>>1)==c);''';assert s.count(x)==1
s=s.replace(x,'''                // Gather four terms from one column run, then retain the exact
                // original left-to-right floating-point addition order.
                while(i+4<=end) {
                    uint32_t ids;std::memcpy(&ids,key.data()+i,4);
                    const auto packed=_mm_i32gather_epi32(next_packed.data(),_mm_cvtepu8_epi32(_mm_cvtsi32_si128(ids)),4);
                    const auto columns=_mm_and_si128(_mm_srli_epi32(packed,17),_mm_set1_epi32(127));
                    if(_mm_movemask_epi8(_mm_cmpeq_epi32(columns,_mm_set1_epi32(c)))!=65535)break;
                    const int colors=_mm_movemask_ps(_mm_castsi128_ps(_mm_slli_epi32(packed,15)));
                    if(first[2*c]<0 && colors!=15)first[2*c]=depth+__builtin_ctz(unsigned(colors^15));
                    if(first[2*c+1]<0 && colors)first[2*c+1]=depth+__builtin_ctz(unsigned(colors));
                    const auto indices=_mm_add_epi32(_mm_and_si128(packed,_mm_set1_epi32(65535)),
                        _mm_add_epi32(_mm_set1_epi32(depth),_mm_setr_epi32(0,1,2,3)));
                    alignas(32) double terms[4];
                    _mm256_store_pd(terms,_mm256_i32gather_pd(depth_terms.data(),indices,8));
                    cost+=terms[0];cost+=terms[1];cost+=terms[2];cost+=terms[3];
                    if(mdp_scan) {
                        const auto types=_mm_srli_epi32(packed,24);
                        code=(code<<8) | (uint32_t(_mm_extract_epi32(types,0))<<6)
                            | (uint32_t(_mm_extract_epi32(types,1))<<4)
                            | (uint32_t(_mm_extract_epi32(types,2))<<2) | uint32_t(_mm_extract_epi32(types,3));
                    }
                    i+=4;depth+=4;
                }
                while(i<end && (next_paper[key[i]].color>>1)==c) {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0)first[np.color]=depth;
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                }''')
for name,source,extra in [('dcomp-t11-scan4',s,''),('dcomp-t11-scan4-check','#define NEXT_PREFIX_CHECK 1\n'+s,'元のscalar next_costでも再計算し、double全bitを照合する。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nnext_costの列内scanで、同じ列の連続4紙の項をAVX2 gatherで得る。色の初出depthとMDPの2bit列も同じ紙順で更新する。4項のdouble加算は元の順序を明示的に維持し、列の境界や64/128 checkpointを跨がない。'+extra+'\n\n違う列が混ざる4紙はscalar経路を使うため、列の並び順を仮定しない。探索予算・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreは保持。fast-mathや時計による切替は使わない。\n')
