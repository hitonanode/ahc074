#define main solver_entry_not_used
#include "../experiments/five_inverse.cpp"
#undef main
#include <map>
#include <set>
#include <queue>
int main(){
    using Perm=std::array<int,5>;
    std::vector<Perm> perms;std::map<Perm,int> index;
    Perm p={0,1,2,3,4};do{index[p]=perms.size();perms.push_back(p);}while(std::next_permutation(p.begin(),p.end()));
    std::vector<std::vector<int>> reverse(120);
    for(int st=0;st<120;st++)for(int from=0;from<4;from++)for(int to=0;to<5;to++)if(from!=to){
        std::vector<int> v(perms[st].begin(),perms[st].end());int k=v[from];v.erase(v.begin()+from);v.insert(v.begin()+to,k);
        Perm q;std::copy(v.begin(),v.end(),q.begin());reverse[index[q]].push_back(st);
    }
    std::set<u64> closures;
    for(int code=0;code<59049;code++){
        int rest=code;unsigned reach[5]={};
        for(int a=0;a<5;a++)for(int b=a+1;b<5;b++){int z=rest%3;rest/=3;if(z==1)reach[a]|=1<<b;if(z==2)reach[b]|=1<<a;}
        for(int k=0;k<5;k++)for(int a=0;a<5;a++)if(reach[a]>>k&1)reach[a]|=reach[k];
        bool cycle=false;u64 c=0;for(int a=0;a<5;a++){cycle|=bool(reach[a]>>a&1);c|=u64(reach[a])<<(8*a);}if(!cycle)closures.insert(c);
    }
    auto independent_sum=[&](u64 c){
        std::array<int,120> d;d.fill(-1);std::queue<int> q;
        for(int st=0;st<120;st++){
            int pos[5];for(int i=0;i<5;i++)pos[perms[st][i]]=i;bool ok=true;
            for(int a=0;a<5;a++)for(int b=0;b<5;b++)if((c>>(8*a+b)&1)&&pos[a]>pos[b])ok=false;
            if(ok)d[st]=0,q.push(st);
        }
        while(!q.empty()){int st=q.front();q.pop();for(int pred:reverse[st])if(d[pred]<0)d[pred]=d[st]+1,q.push(pred);}
        return std::accumulate(d.begin(),d.end(),0);
    };
    int errors=0;
    for(u64 c:closures){u64 dual=0;for(int a=0;a<5;a++)for(int b=0;b<5;b++)if(c>>(8*a+b)&1)dual|=1ULL<<(8*b+a);
        int expected=6*(independent_sum(c)+independent_sum(dual));if(expected!=five_scaled_sum(c))errors++;}
    std::cout<<"{\"labeled_posets\":"<<closures.size()<<",\"independently_computed_distance_entries\":"<<closures.size()*240
             <<",\"errors\":"<<errors<<"}\n";return errors!=0;
}
