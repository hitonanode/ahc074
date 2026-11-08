from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
old='''        const uint8_t k = o[p];
        if (p < dest)
            std::memmove(&o[p], &o[p + 1], dest - p);
        else
            std::memmove(&o[dest + 1], &o[dest], p - dest);
        o[dest] = k;''';assert b.count(old)==1
for name,small in [('shiftzero',False),('shift64',True)]:
 new='''        if(p==dest)return;
        const uint8_t k=o[p];
'''
 if small:new+='''        const int n=std::abs(p-dest);
        uint8_t* dst=p<dest?&o[p]:&o[dest+1];
        const uint8_t* src=p<dest?&o[p+1]:&o[dest];
        // Load every covered byte before writing: these ranges overlap by n-1.
        // The head and tail stores agree wherever they overlap each other.
        if(n>=32 && n<=64) {
            __m128i a=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src));
            __m128i b=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src+16));
            __m128i c=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src+n-32));
            __m128i d=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src+n-16));
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst),a);
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst+16),b);
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst+n-32),c);
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst+n-16),d);
        } else if(n>=16 && n<32) {
            __m128i a=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src));
            __m128i b=_mm_loadu_si128(reinterpret_cast<const __m128i*>(src+n-16));
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst),a);
            _mm_storeu_si128(reinterpret_cast<__m128i*>(dst+n-16),b);
        } else if(n>=8 && n<16) {
            u64 a,b;std::memcpy(&a,src,8);std::memcpy(&b,src+n-8,8);
            std::memcpy(dst,&a,8);std::memcpy(dst+n-8,&b,8);
        } else if(n>=4 && n<8) {
            uint32_t a,b;std::memcpy(&a,src,4);std::memcpy(&b,src+n-4,4);
            std::memcpy(dst,&a,4);std::memcpy(dst+n-4,&b,4);
        } else if(n>=2 && n<4) {
            uint16_t a,b;std::memcpy(&a,src,2);std::memcpy(&b,src+n-2,2);
            std::memcpy(dst,&a,2);std::memcpy(dst+n-2,&b,2);
        } else if(n==1)*dst=*src;
        else std::memmove(dst,src,n);
'''
 else:new+='''        if(p<dest)std::memmove(&o[p],&o[p+1],dest-p);
        else std::memmove(&o[dest+1],&o[dest],p-dest);
'''
 new+='''        o[dest]=k;'''
 s=b.replace(old,new)
 d=S/('dcomp-t12-'+name);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\nbyte配列の紙移動で同じ位置なら直ちに戻る。'+('64 bytes以下のmemmoveは全範囲を先にregisterへ読み、head/tailを同じ順序位置へ書く。整数操作のみ、overlap部分は同じ値を持つ。'if small else '大きさ0のmemmove呼出しと同一byteへの代入を省く対照。')+'\n\n計測時計の負荷を含む絶対値は速度利益の推定に使わず、通常版の同時比較とbyte一致で採否を決める。既存ログ・trace・profiler・実験switch・段・DesignStoreを保持。予算・時計分岐なし。\n')
