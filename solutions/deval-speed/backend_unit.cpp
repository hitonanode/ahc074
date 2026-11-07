#include <algorithm>
#include <array>
#include <vector>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <cassert>
#include <iostream>
#include <immintrin.h>
struct Test {
    struct Filler {
        int paper;
        int lvl = 0, hi = 0;
    };
    // State snapshots normally have at most four fillers. Copy those records
    // inline; the overflow path retains the vector's unbounded semantics.
    class FillerList {
        static constexpr size_t Inline=4;
        std::array<Filler,Inline> local_;
        std::vector<Filler> large_;
        size_t count_=0;
    public:
        FillerList()=default;
        FillerList(std::initializer_list<Filler> init){assign(init.begin(),init.end());}
        FillerList(const FillerList& other){assign(other.begin(),other.end());}
        FillerList(FillerList&& other) noexcept { *this=std::move(other); }
        FillerList& operator=(const FillerList& other) {
            if(this!=&other)assign(other.begin(),other.end());return *this;
        }
        FillerList& operator=(FillerList&& other) noexcept {
            if(this==&other)return *this;
            count_=other.count_;
            if(count_<=Inline)std::copy_n(other.local_.data(),count_,local_.data());
            else large_=std::move(other.large_);
            other.count_=0;return *this;
        }
        size_t size()const{return count_;}
        bool empty()const{return count_==0;}
        Filler* begin(){return count_<=Inline?local_.data():large_.data();}
        const Filler* begin()const{return count_<=Inline?local_.data():large_.data();}
        Filler* end(){return begin()+count_;}
        const Filler* end()const{return begin()+count_;}
        Filler& operator[](size_t i){return begin()[i];}
        const Filler& operator[](size_t i)const{return begin()[i];}
        Filler& back(){return begin()[count_-1];}
        const Filler& back()const{return begin()[count_-1];}
        template<class It> void assign(It first,It last) {
            const size_t size=last-first;
            if(size<=Inline)std::copy(first,last,local_.begin());
            else large_.assign(first,last);
            count_=size;
        }
        void push_back(Filler value) {
            if(count_<Inline)local_[count_]=value;
            else {
                if(count_==Inline)large_.assign(local_.begin(),local_.end());
                large_.push_back(value);
            }
            ++count_;
        }
        template<class Pred> void erase_if(Pred pred) {
            Filler* start=begin();const auto last=std::remove_if(start,start+count_,pred);
            const size_t size=last-start;
            if(count_>Inline) {
                if(size<=Inline)std::copy_n(start,size,local_.data());
                else large_.resize(size);
            }
            count_=size;
        }
    };
};
std::vector<int> original(const std::vector<std::vector<double>>& cost) {
    
    int n = cost.size();
    std::vector<double> u(n + 1), v(n + 1);
    std::vector<int> p(n + 1), way(n + 1);
    std::vector<double> minv(n + 1);
    std::vector<uint8_t> used(n + 1);
    for (int i = 1; i <= n; i++) {
        p[0] = i;
        int j0 = 0;
        std::fill(minv.begin(), minv.end(), 1e100);
        std::fill(used.begin(), used.end(), 0);
        do {
            used[j0] = true;
            int i0 = p[j0], j1 = 0;
            double delta = 1e100;
            for (int j = 1; j <= n; j++)
                if (!used[j]) {
                    double cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
                    if (cur < minv[j]) minv[j] = cur, way[j] = j0;
                    if (minv[j] < delta) delta = minv[j], j1 = j;
                }
            for (int j = 0; j <= n; j++)
                if (used[j])
                    u[p[j]] += delta, v[j] -= delta;
                else
                    minv[j] -= delta;
            j0 = j1;
        } while (p[j0]);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    std::vector<int> answer(n);
    for (int j = 1; j <= n; j++) answer[p[j] - 1] = j - 1;
    return answer;
}


__attribute__((target("avx2"))) std::vector<int> hungarian(const std::vector<std::vector<double>>& cost) {
    
    int n = cost.size();
    std::vector<double> u(n + 1), v(n + 1);
    std::vector<int> p(n + 1), way(n + 1);
    std::vector<double> minv(n + 1);
    std::vector<uint8_t> used(n + 1);
    std::vector<int> visited(n + 1);
    for (int i = 1; i <= n; i++) {
        p[0] = i;
        int j0 = 0, visited_count = 0;
        std::fill(minv.begin(), minv.end(), 1e100);
        std::fill(used.begin(), used.end(), 0);
        do {
            used[j0] = true;
            visited[visited_count++]=j0;
            int i0 = p[j0], j1 = 0;
            double delta = 1e100;
            // Four independent columns; reduction ties use the lower column
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
            for(int q=0;q<visited_count;++q) {
                const int j=visited[q];
                u[p[j]]+=delta;v[j]-=delta;
            }
            // A visited column is never read from minv again in this search.
            // Updating its dead slack too permits a branch-free vector loop;
            // every live slack has exactly the original subtraction sequence.
            for(int j=1;j<=n;++j)minv[j]-=delta;
            j0 = j1;
        } while (p[j0]);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    std::vector<int> answer(n);
    for (int j = 1; j <= n; j++) answer[p[j] - 1] = j - 1;
    return answer;
}


int main(){
    uint64_t rng=37484691;
    auto next=[&](){rng^=rng<<13;rng^=rng>>7;return rng^=rng<<17;};
    Test::FillerList a,b;std::vector<Test::Filler> x,y;
    auto eq=[](const auto& a,const auto& b){assert(a.size()==b.size());for(size_t i=0;i<a.size();++i)assert(a[i].paper==b[i].paper&&a[i].lvl==b[i].lvl&&a[i].hi==b[i].hi);};
    for(int it=0;it<100000;++it){
        const int op=next()%6;
        if(op==0&&x.size()<192){Test::Filler f{int(next()%192),int(next()%35),int(next()%35)};a.push_back(f);x.push_back(f);}
        if(op==1){const int m=next()%7;auto pred=[&](auto f){return f.paper%7==m;};a.erase_if(pred);std::erase_if(x,pred);}
        if(op==2){b=a;y=x;}
        if(op==3){a=b;x=y;}
        if(op==4){Test::FillerList c(a);a=std::move(c);}
        if(op==5){std::sort(a.begin(),a.end(),[](auto f,auto g){return f.paper<g.paper;});std::sort(x.begin(),x.end(),[](auto f,auto g){return f.paper<g.paper;});}
        eq(a,x);eq(b,y);
    }
    for(int it=0;it<500;++it){const int n=1+next()%50;std::vector cost(n,std::vector<double>(n));
        for(auto& row:cost)for(auto& v:row)v=int(next()%17)*.1;
        assert(original(cost)==hungarian(cost));
    }
    std::cout<<"filler operations=100000, tied Hungarian matrices=500: PASS\n";
}
