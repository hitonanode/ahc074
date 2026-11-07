from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
s=s.replace('#include <algorithm>','#include <algorithm>\n#include <initializer_list>',1)
s=s.replace('std::vector<Filler>','FillerList')
idx=s.index('    FillerList fillers;')
s=s[:idx]+'''    // State snapshots normally have at most four fillers. Copy those records
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
'''+s[idx:]
s=s.replace('std::erase_if(fillers, [&](const Filler& f) { return f.paper == k; });','fillers.erase_if([&](const Filler& f) { return f.paper == k; });',1)
d=ROOT/'solutions/deval-smallfill';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-smallfill

改良元: solutions/deval-vbranch-o3。

注文の状態保存で使うfiller列を、4枚まではオブジェクト内に保持する小さな可変長配列に置き換える。5枚以上は従来と同じvectorを使う。並び順・コピーする値・探索予算・浮動小数点の計算・時間ガードは同じで、短い列のヒープ確保だけを減らす。
''')
print(len(s.encode()))
