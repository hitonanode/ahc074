from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='    using Moves = std::vector<std::pair<int, int>>;';assert B.count(a)==1
code=r'''    // Small request paths avoid heap allocation. Long experimental paths retain
    // the vector overflow; only the live prefix is copied between inline paths.
    class Moves {
        using Item=std::pair<int,int>;
        static constexpr size_t Inline=24;
        std::array<Item,Inline> local_;
        std::vector<Item> large_;
        size_t count_=0;
        void grow(size_t n) {
            if(n>Inline) {
                if(count_<=Inline)large_.assign(local_.begin(),local_.begin()+count_);
                large_.resize(n);
            }
        }
    public:
        Moves()=default;
        Moves(std::initializer_list<Item> x){assign(x.begin(),x.end());}
        template<class It> Moves(It first,It last){assign(first,last);}
        Moves(const Moves& x){assign(x.begin(),x.end());}
        Moves(Moves&& x)noexcept{*this=std::move(x);}
        Moves& operator=(const Moves& x){if(this!=&x)assign(x.begin(),x.end());return *this;}
        Moves& operator=(Moves&& x)noexcept {
            if(this==&x)return *this;
            count_=x.count_;
            if(count_<=Inline)std::copy_n(x.local_.begin(),count_,local_.begin());
            else large_=std::move(x.large_);
            x.count_=0;return *this;
        }
        Moves& operator=(const std::vector<Item>& x){assign(x.begin(),x.end());return *this;}
        Item* data(){return count_<=Inline?local_.data():large_.data();}
        const Item* data()const{return count_<=Inline?local_.data():large_.data();}
        Item* begin(){return data();}const Item* begin()const{return data();}
        Item* end(){return data()+count_;}const Item* end()const{return data()+count_;}
        size_t size()const{return count_;}bool empty()const{return count_==0;}
        Item& operator[](size_t i){return data()[i];}const Item& operator[](size_t i)const{return data()[i];}
        Item& back(){return data()[count_-1];}const Item& back()const{return data()[count_-1];}
        void clear(){count_=0;}
        void reserve(size_t n){if(n>Inline)large_.reserve(n);}
        template<class It> void assign(It first,It last) {
            const size_t n=last-first;
            if(n<=Inline)std::copy(first,last,local_.begin());else large_.assign(first,last);
            count_=n;
        }
        void push_back(Item v){const size_t n=count_;grow(n+1);count_=n+1;data()[n]=v;}
        template<class... A> Item& emplace_back(A&&... a){push_back(Item(std::forward<A>(a)...));return back();}
        void resize(size_t n) {
            if(n<=Inline) {
                if(count_>Inline)std::copy_n(large_.begin(),n,local_.begin());
                else if(n>count_)std::fill(local_.begin()+count_,local_.begin()+n,Item{});
            } else grow(n);
            count_=n;
        }
        template<class It> Item* insert(const Item* where,It first,It last) {
            const size_t at=where-data(),m=last-first,n=count_;grow(n+m);count_=n+m;
            auto p=data();std::move_backward(p+at,p+n,p+n+m);std::copy(first,last,p+at);return p+at;
        }
        Item* insert(const Item* where,Item item){return insert(where,&item,&item+1);}
        Item* erase(const Item* first,const Item* last) {
            const size_t a=first-data(),b=last-data(),n=count_-(b-a);
            std::move(begin()+b,end(),begin()+a);resize(n);return begin()+a;
        }
        Item* erase(const Item* p){return erase(p,p+1);}
        friend bool operator==(const Moves& a,const Moves& b){return a.size()==b.size()&&std::equal(a.begin(),a.end(),b.begin());}
    };'''
s=B.replace(a,code)
d=R/'solutions/dcomp-t11-smallmoves';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n要求の操作列Movesを24要素のinline格納とし、長い列はstd::vectorへ移す。操作や比較の順序は変えず、live要素だけをコピーする。構造は既存FillerListと同じ方針。両コンパイラで親との出力byte一致と時間を確認する。\n\n固定予算・実験スイッチ・ログとprofiler・目次と段・DesignStoreを保持。時計による切替は追加しない。\n')
