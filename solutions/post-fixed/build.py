from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-tight/main.cpp').read_text()
definition='''// Short edit and stack lists avoid an allocation for every discarded trial.
// Only live elements are copied; unused capacity is deliberately uninitialized.
template<class T,int Capacity>struct TrialList {
    T data_[Capacity];int count=0;
    TrialList()=default;
    TrialList(const TrialList&o):count(o.count){std::copy_n(o.data_,count,data_);}
    TrialList&operator=(const TrialList&o){if(this!=&o){count=o.count;std::copy_n(o.data_,count,data_);}return *this;}
    TrialList(const std::vector<T>&o):count(o.size()){assert(count<=Capacity);std::copy(o.begin(),o.end(),data_);}
    TrialList&operator=(const std::vector<T>&o){count=o.size();assert(count<=Capacity);std::copy(o.begin(),o.end(),data_);return *this;}
    T*begin(){return data_;}const T*begin()const{return data_;}
    T*end(){return data_+count;}const T*end()const{return data_+count;}
    int size()const{return count;}bool empty()const{return count==0;}
    T&operator[](int i){return data_[i];}const T&operator[](int i)const{return data_[i];}
    void reserve(int n){assert(n<=Capacity);}void clear(){count=0;}
    void push_back(const T&t){assert(count<Capacity);data_[count++]=t;}
    T*erase(T*at){int i=at-data_;assert(i>=0&&i<count);std::move(data_+i+1,data_+count,data_+i);count--;return data_+i;}
    T*insert(T*at,const T&t){int i=at-data_;assert(i>=0&&i<=count&&count<Capacity);std::move_backward(data_+i,data_+count,data_+count+1);data_[i]=t;count++;return data_+i;}
};
'''
s=s.replace('struct Solver {',definition+'\nstruct Solver {')
s=s.replace('static constexpr bool byte_links=true;','static constexpr bool byte_links=true;\n    static inline bool fixed_lists=false;')
s=s.replace('''        if(byte_links)return post_optimize_links<uint8_t>(initial,std::move(input_ops),u,only_eject);''','''        if(fixed_lists)return post_optimize_links<uint8_t,true>(initial,std::move(input_ops),u,only_eject);
        if(byte_links)return post_optimize_links<uint8_t,false>(initial,std::move(input_ops),u,only_eject);''')
s=s.replace('template<class Link>\n    std::vector<std::pair<int,int>> post_optimize_links','template<class Link,bool Fixed=false>\n    std::vector<std::pair<int,int>> post_optimize_links')
if 'template<class Link,bool Fixed=false>' not in s:
 s=s.replace('template<class Link>','template<class Link,bool Fixed=false>')
a=s.index('template<class Link,bool Fixed=false>');b=s.index('    long long unsafe_plans',a)
body=s[a:b]
needle='''        auto anchorize = [&]'''
body=body.replace(needle,'''        using EditList=std::conditional_t<Fixed,TrialList<Edit,2*K>,std::vector<Edit>>;
        using OrderList=std::conditional_t<Fixed,TrialList<int,K>,std::vector<int>>;
        auto anchorize = [&]''')
body=body.replace('std::vector<Edit>', 'EditList')
body=body.replace('TrialList<Edit,2*K>,EditList','TrialList<Edit,2*K>,std::vector<Edit>')
body=body.replace('std::vector<int> ord','OrderList ord').replace('std::vector<int>ord','OrderList ord')
body=body.replace('order = std::move(ord);','order.assign(ord.begin(),ord.end());')
# The baseline vector branch should retain its original move assignment.
body=body.replace('order.assign(ord.begin(),ord.end());','if constexpr(Fixed)order.assign(ord.begin(),ord.end());else order=std::move(ord);')
s=s[:a]+body+s[b:]
if '#include <type_traits>'not in s:s=s.replace('#include <vector>','#include <vector>\n#include <type_traits>')
(p/'main.cpp').write_text(s)
