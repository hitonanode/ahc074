from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-climbcache/main.cpp').read_text()
needle='    using Moves = std::vector<std::pair<int, int>>;'
repl='''    struct Move { int first,second; bool operator==(const Move&) const=default; };
    // The common short path owns its records directly. Overflow remains dynamic;
    // copying and moving touch only live entries, including after shrink/clear.
    class Moves {
        static constexpr size_t Inline=16;
        std::array<Move,Inline> local_;
        std::vector<Move> large_;
        size_t count_=0;
    public:
        Moves()=default;
        Moves(std::initializer_list<Move> init){assign(init.begin(),init.end());}
        Moves(const Moves& o){assign(o.begin(),o.end());}
        Moves(Moves&& o)noexcept{*this=std::move(o);}
        Moves& operator=(const Moves& o){if(this!=&o)assign(o.begin(),o.end());return *this;}
        Moves& operator=(Moves&& o)noexcept{
            if(this==&o)return *this;
            count_=o.count_;
            if(count_<=Inline)std::copy_n(o.local_.data(),count_,local_.data());
            else large_=std::move(o.large_);
            o.count_=0;return *this;
        }
        size_t size()const{return count_;}
        bool empty()const{return count_==0;}
        Move* begin(){return count_<=Inline?local_.data():large_.data();}
        const Move* begin()const{return count_<=Inline?local_.data():large_.data();}
        Move* end(){return begin()+count_;}
        const Move* end()const{return begin()+count_;}
        Move& operator[](size_t i){return begin()[i];}
        const Move& operator[](size_t i)const{return begin()[i];}
        Move& back(){return begin()[count_-1];}
        const Move& back()const{return begin()[count_-1];}
        void clear(){count_=0;}
        template<class It>void assign(It first,It last){
            const size_t n=last-first;
            if(n<=Inline)std::copy(first,last,local_.begin());
            else large_.assign(first,last);
            count_=n;
        }
        void push_back(Move value){
            if(count_<Inline)local_[count_]=value;
            else {if(count_==Inline)large_.assign(local_.begin(),local_.end());large_.push_back(value);}
            ++count_;
        }
        void resize(size_t n){
            if(n<=Inline){
                if(count_>Inline)std::copy_n(large_.data(),n,local_.data());
                else if(n>count_)std::fill(local_.begin()+count_,local_.begin()+n,Move{});
            }else{
                if(count_<=Inline)large_.assign(local_.begin(),local_.begin()+count_);
                large_.resize(n);
            }
            count_=n;
        }
        template<class It>void insert(Move* where,It first,It last){
            // Every path insertion appends a separate memoized suffix.
            assert(where==end());
            const size_t old=count_,added=last-first;
            resize(old+added);std::copy(first,last,begin()+old);
        }
        bool operator==(const Moves& o)const{return count_==o.count_&&std::equal(begin(),end(),o.begin());}
    };'''
assert s.count(needle)==1;s=s.replace(needle,repl,1)
start=s.index('    void set_generic(int u, u64 holes) {')
pos=s.index('        Moves path;',start)
s=s[:pos]+s[pos:].replace('        Moves path;','        std::vector<std::pair<int,int>> path;',1)
d=R/'solutions/deval-smallmoves';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-smallmoves

改良元: solutions/deval-climbcache。

注文計画の操作列を、通常の16操作まではオブジェクト内に持つ。長い列は動的vectorへ移すので、操作数の上限や探索結果は変えない。保存状態・メモ・後処理候補の操作列の短いコピーでヒープ確保を減らす。append、縮小、clear後の再利用を含めてvectorと照合する。

設計・注文の探索回数は親と同じ。時間不足による切替えはない。ログ、DesignStore、@paper/@ops、目次と段の目印を維持。
''')
# Extract only the independent storage class for its semantic test.
unit='''#include <array>
#include <vector>
#include <algorithm>
#include <cassert>
#include <initializer_list>
#include <random>
#include <iostream>
struct Test {\n'''+repl+'''\n};
int main(){
 std::mt19937 gen(93245);Test::Moves a,b;std::vector<Test::Move> x,y;
 auto check=[&](){assert(a.size()==x.size());assert(b.size()==y.size());assert(std::equal(a.begin(),a.end(),x.begin()));assert(std::equal(b.begin(),b.end(),y.begin()));};
 for(int step=0;step<100000;++step){
  switch(gen()%9){
   case 0:{Test::Move v{int(gen()),int(gen())};a.push_back(v);x.push_back(v);break;}
   case 1:{size_t n=gen()%80;a.resize(n);x.resize(n);break;}
   case 2:b=a;y=x;break;
   case 3:a=std::move(b);x=std::move(y);y.clear();break;
   case 4:a.clear();x.clear();break;
   case 5:a.assign(b.begin(),b.end());x.assign(y.begin(),y.end());break;
   case 6:a.insert(a.end(),b.begin(),b.end());x.insert(x.end(),y.begin(),y.end());break;
   case 7:{Test::Moves c(a);std::vector<Test::Move> z(x);a=std::move(c);x=std::move(z);break;}
   case 8:{Test::Move v{int(gen()),int(gen())};b.push_back(v);y.push_back(v);break;}
  }
  check();if(x.size()+y.size()>10000){a.clear();b.clear();x.clear();y.clear();}
 }
 std::cout<<"100000 storage operations PASS\\n";
}
'''
(R/'solutions/deval-speed/smallmoves_unit.cpp').write_text(unit)
print(len(s.encode()))
