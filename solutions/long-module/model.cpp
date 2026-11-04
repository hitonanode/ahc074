#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using State=std::vector<unsigned char>;
struct Event {int paper,mask,color;};
struct Node {State order;double value;};
struct Model {
    int K,P,W=3,full=7,width=8,potential_mode=0;bool fast_insert=true;
    std::vector<int> physical,column,op,color,allowed,weight;
    std::vector<Event> events;
    mutable long long repair_calls=0,fallback_calls=0,fallback_moves=0;
    std::array<std::array<double,2>,5> demand{};
    struct Demand {int mask,color;double weight;unsigned matches;};std::vector<Demand> joint_demand;
    Model(const char* file,int beam):width(beam){
        std::ifstream in(file);std::string header;std::getline(in,header);std::stringstream hs(header);hs>>K>>P;if(!(hs>>W))W=3;full=(1<<W)-1;assert(K>0&&K<64&&P==256&&W>=3&&W<=5);
        physical.resize(K);column.resize(K);op.resize(K);color.resize(K);allowed.resize(K);weight.resize(K);
        for(int k=0;k<K;k++)in>>physical[k]>>column[k]>>op[k]>>color[k]>>allowed[k];
        events.resize(P);for(auto& e:events){in>>e.paper>>e.mask>>e.color;if(e.paper>=0)weight[e.paper]++;}assert(in);
        update();
    }
    bool can(int mask,int target,int removed=-1)const{
        unsigned long long remaining=K==64?~0ULL:(1ULL<<K)-1;if(removed>=0)remaining&=~(1ULL<<removed);
        while(mask){bool progress=false;for(int k=0;k<K;k++)if((remaining>>k&1)&&!((color[k]^target)&op[k]&mask)){mask&=~op[k];remaining&=~(1ULL<<k);progress=true;}if(!progress)return false;}return true;
    }
    bool update(){
        demand={};joint_demand.clear();std::array<std::array<int,32>,32> joint{};for(auto e:events){if(e.paper>=0)e.mask=full&~op[e.paper];if(!can(e.mask,e.color,e.paper))return false;joint[e.mask][e.color&e.mask]++;for(int j=0;j<W;j++)if(e.mask>>j&1)demand[j][e.color>>j&1]+=1.0/P;}
        for(int mask=1;mask<=full;mask++)for(int color=0;color<=full;color++)if(joint[mask][color]){unsigned matches=0;for(int v=0;v<=full;v++)if((v&mask)==color)matches|=1U<<v;joint_demand.push_back({mask,color,double(joint[mask][color])/P,matches});}return true;
    }
    struct View {int display=0,key=0;std::array<int,5> first{-1,-1,-1,-1,-1};std::array<int,5> visible{-1,-1,-1,-1,-1};int n=0;};
    View view(const State& s)const{
        View v;int covered=0;for(int k:s){int shown=op[k]&~covered;if(!shown)continue;v.visible[v.n++]=k;v.display|=color[k]&shown;for(int j=0;j<W;j++)if(shown>>j&1)v.first[j]=k;covered|=op[k];if(covered==full)break;}
        for(int j=0;j<W;j++)v.key|=(v.first[j]+1)<<(6*j);return v;
    }
    double value(const State& s)const{
        std::array<int,5> count{};std::array<std::array<int,2>,5> first;for(auto& a:first)a={K,K};double v=0;
        for(int k:s){int rank=K;for(int j=0;j<W;j++)if(op[k]>>j&1){rank=std::min(rank,count[j]);int b=color[k]>>j&1;if(first[j][b]==K)first[j][b]=count[j];count[j]++;}v+=double(weight[k]*rank)/P;}
        double old_repair=0;for(int j=0;j<W;j++)for(int b=0;b<2;b++)old_repair+=demand[j][b]*first[j][b];
        if(!potential_mode)return v+old_repair;
        auto [current_display,one]=one_displays(s);
        double coupled=0;for(auto d:joint_demand)if((current_display&d.mask)!=d.color)coupled+=d.weight*((one&d.matches)?1:2);
        if(potential_mode>=3){double credit=0;for(auto d:joint_demand)if((current_display&d.mask)!=d.color&&(one&d.matches)){int separate=0;for(int j=0;j<W;j++)if(d.mask>>j&1)separate+=first[j][d.color>>j&1];credit+=d.weight*std::max(0,separate-1);}return v+old_repair-credit*(potential_mode==3?1:.5);}
        double mix=.5*potential_mode;return v+(1-mix)*old_repair+mix*coupled;
    }
    std::pair<int,unsigned> one_displays(const State& s)const {
        // All displays reachable in one legal move, using the first and second
        // opaque papers at each local window. Only crossing one of these first
        // positions can change the display after reinserting a visible paper.
        std::array<int,5> head,second;head.fill(-1);second.fill(-1);
        for(int i=0;i<int(s.size());i++)for(int j=0;j<W;j++)if(op[s[i]]>>j&1){if(head[j]<0)head[j]=i;else if(second[j]<0)second[j]=i;}
        int current_display=0;std::array<int,5> visible{};int nv=0;
        for(int j=0;j<W;j++)if(head[j]>=0){current_display|=(color[s[head[j]]]&1<<j);int h=head[j];if(std::find(visible.begin(),visible.begin()+nv,h)==visible.begin()+nv)visible[nv++]=h;}
        unsigned one=1U<<current_display;
        for(int a=0;a<nv;a++){
            int pos=visible[a],k=s[pos],base=0;std::array<int,5> after;std::array<int,6> stops{};int ns=1;
            for(int j=0;j<W;j++){int ix=head[j]==pos?second[j]:head[j];after[j]=ix<0?int(s.size()):ix-int(ix>pos);if(ix>=0)base|=color[s[ix]]&(1<<j);if(op[k]>>j&1)stops[ns++]=after[j]+1;}
            for(int z=0;z<ns;z++){if(stops[z]>=int(s.size()))continue;int display=base;for(int j=0;j<W;j++)if((op[k]>>j&1)&&stops[z]<=after[j])display=(display&~(1<<j))|(color[k]&(1<<j));one|=1U<<display;}
        }
        return {current_display,one};
    }
    static State moved(const State& s,int k,int depth){State t=s;auto it=std::find(t.begin(),t.end(),k);assert(it!=t.end());t.erase(it);t.insert(t.begin()+depth,k);return t;}
    // Price every insertion in O(K W). For an existing paper, inserting k
    // before it raises its minimum blocking depth iff all windows attaining
    // that minimum are opaque on k. These contributions form a suffix sum.
    std::vector<double> insertion_values(const State& base,int k)const {
        int n=base.size();std::vector<double> prices(n+1);
        if(potential_mode){for(int d=0;d<=n;d++){State t=base;t.insert(t.begin()+d,k);prices[d]=value(t);}return prices;}
        std::array<int,5> count{};std::array<std::array<int,2>,5> first_depth,first_pos;
        for(auto& a:first_depth)a={K,K};for(auto& a:first_pos)a={-1,-1};
        std::vector<int> suffix(n+1);int base_rank=0;
        for(int i=0;i<n;i++){
            int x=base[i],rank=K,minways=0;
            for(int j=0;j<W;j++)if(op[x]>>j&1){if(count[j]<rank){rank=count[j];minways=1<<j;}else if(count[j]==rank)minways|=1<<j;int b=color[x]>>j&1;if(first_pos[j][b]<0){first_depth[j][b]=count[j];first_pos[j][b]=i;}count[j]++;}
            base_rank+=weight[x]*rank;suffix[i]=weight[x]*int(!(minways&~op[k]));
        }
        for(int i=n-1;i>=0;i--)suffix[i]+=suffix[i+1];count={};
        for(int d=0;d<=n;d++){
            int rank=K;for(int j=0;j<W;j++)if(op[k]>>j&1)rank=std::min(rank,count[j]);
            double price=double(base_rank+suffix[d]+weight[k]*rank)/P;
            for(int j=0;j<W;j++)for(int b=0;b<2;b++){
                int depth=first_depth[j][b];if(op[k]>>j&1){if((color[k]>>j&1)==b)depth=std::min(depth,count[j]);else if(first_pos[j][b]>=d)depth++;}price+=demand[j][b]*depth;
            }
            prices[d]=price;if(d<n)for(int j=0;j<W;j++)count[j]+=op[base[d]]>>j&1;
        }
        return prices;
    }
    std::pair<double,State> insert_best(const State& s,int k)const{
        if(!fast_insert){double best=1e100;State order;for(int i=0;i<=int(s.size());i++){State t=s;t.insert(t.begin()+i,k);double v=value(t);if(v<best){best=v;order=std::move(t);}}return {best,std::move(order)};}
        auto prices=insertion_values(s,k);int pos=std::min_element(prices.begin(),prices.end())-prices.begin();State t=s;t.insert(t.begin()+pos,k);return {prices[pos],std::move(t)};
    }
    // Different insertion positions with identical visible paper identities
    // have the same immediate display. Keep the best future value per group.
    void expand_slow(const State& s,std::vector<Node>& out)const{
        auto head=view(s);int n=s.size();
        for(int a=0;a<head.n;a++){
            int k=head.visible[a];std::array<int,6> keys{};std::array<Node,6> best;int groups=0;
            for(int d=0;d<n;d++){
                State t=moved(s,k,d);if(t==s)continue;int key=view(t).key,g=0;while(g<groups&&keys[g]!=key)g++;
                double price=value(t);
                if(g==groups){assert(groups<=W);keys[groups++]=key;best[g]={std::move(t),price};}
                else if(price<best[g].value)best[g]={std::move(t),price};
            }
            for(int g=0;g<groups;g++)out.push_back(std::move(best[g]));
        }
    }
    void expand(const State& s,std::vector<Node>& out)const {
        if(!fast_insert){expand_slow(s,out);return;}auto head=view(s);
        for(int a=0;a<head.n;a++){
            int k=head.visible[a],oldpos=std::find(s.begin(),s.end(),k)-s.begin();State base=s;base.erase(base.begin()+oldpos);auto prices=insertion_values(base,k);
            std::array<int,5> first_pos,first_id;first_pos.fill(base.size());first_id.fill(-1);
            for(int i=0;i<int(base.size());i++)for(int j=0;j<W;j++)if(first_id[j]<0&&(op[base[i]]>>j&1)){first_pos[j]=i;first_id[j]=base[i];}
            std::array<int,6> keys{},depth{};std::array<double,6> best;int groups=0;
            for(int d=0;d<=int(base.size());d++)if(d!=oldpos){
                int key=0;for(int j=0;j<W;j++){int first=((op[k]>>j&1)&&d<=first_pos[j])?k:first_id[j];key|=(first+1)<<(6*j);}int g=0;while(g<groups&&keys[g]!=key)g++;
                if(g==groups){assert(groups<=W);keys[groups++]=key;best[g]=prices[d];depth[g]=d;}else if(prices[d]<best[g]){best[g]=prices[d];depth[g]=d;}
            }
            for(int g=0;g<groups;g++){State t=base;t.insert(t.begin()+depth[g],k);out.push_back({std::move(t),best[g]});}
        }
    }
    struct Plan {int moves=100000;State order;};
    Plan repair(const State& initial,int mask,int target,int held=-1)const{
        repair_calls++;std::vector<Node> beam{{initial,value(initial)}};
        for(int depth=0;depth<=10;depth++){
            double best=1e100;State goal;
            for(const auto& node:beam)if(!((view(node.order).display^target)&mask)){
                auto result=held<0?std::make_pair(node.value,node.order):insert_best(node.order,held);
                if(result.first<best){best=result.first;goal=std::move(result.second);}
            }
            if(best<1e90)return {depth,std::move(goal)};
            std::vector<Node> next;for(const auto& node:beam)expand(node.order,next);
            // A cheap distance estimate guides the beam; value alone would
            // prefer a good storage order which does not fix this request.
            for(auto& node:next)node.value+=1.2*__builtin_popcount(unsigned((view(node.order).display^target)&mask));
            std::sort(next.begin(),next.end(),[](const auto& a,const auto& b){return a.value<b.value;});
            beam.clear();for(auto& node:next){bool duplicate=false;for(const auto& old:beam)duplicate|=node.order==old.order;if(duplicate)continue;node.value=value(node.order);beam.push_back(std::move(node));if(int(beam.size())==width)break;}
            if(beam.empty())break;
        }
        // Finish a feasible request by repeatedly retiring an actually wrong
        // visible paper. This is a bounded path in the same printed module.
        fallback_calls++;State s=initial;int steps=0;
        while(steps<6*K){auto v=view(s);int bad=(v.display^target)&mask;if(!bad){fallback_moves+=steps;if(held>=0)s=insert_best(s,held).second;return {steps,std::move(s)};}int j=__builtin_ctz(unsigned(bad)),k=v.first[j];if(k<0)break;s=moved(s,k,s.size()-1);steps++;}
        return {};
    }
    Plan access(const State& initial,int requested,int target)const{
        Plan best;double best_score=1e100;
        for(int j=0;j<W;j++)if(op[requested]>>j&1){
            State s=initial;int moves=0;
            while(true){int k=-1;for(int x:s){if(x==requested)break;if(op[x]>>j&1){k=x;break;}}if(k<0)break;
                int target_pos=std::find(s.begin(),s.end(),requested)-s.begin();double value_best=1e100;State next;
                if(fast_insert){State base=s;base.erase(std::find(base.begin(),base.end(),k));auto prices=insertion_values(base,k);int pos=target_pos;for(int d=target_pos;d<int(s.size());d++)if(prices[d]<prices[pos])pos=d;next=base;next.insert(next.begin()+pos,k);}
                else for(int d=target_pos;d<int(s.size());d++){State t=moved(s,k,d);double v=value(t);if(v<value_best){value_best=v;next=std::move(t);}}
                assert(!next.empty());s=std::move(next);moves++;
            }
            auto v=view(s);assert(std::find(v.visible.begin(),v.visible.begin()+v.n,requested)!=v.visible.begin()+v.n);
            s.erase(std::find(s.begin(),s.end(),requested));auto plan=repair(s,full&~op[requested],target,requested);plan.moves+=moves;
            if(plan.order.empty())continue;double score=plan.moves+value(plan.order);
            if(score<best_score){best_score=score;best=std::move(plan);}
        }
        return best;
    }
    double simulate(int length,std::uint64_t seed)const{
        repair_calls=fallback_calls=fallback_moves=0;State state(K);std::iota(state.begin(),state.end(),0);std::mt19937_64 rng(seed);int previous=rng()%P;long long count=0;
        for(int i=0;i<length;i++){
            int u=i?int(rng()%(P-1)):previous;if(i&&u>=previous)u++;previous=u;auto e=events[u];
            Plan p=e.paper<0?repair(state,e.mask,e.color):access(state,e.paper,e.color);
            if(p.moves>=100000||int(p.order.size())!=K)return 1e6;
            // For external requests the displayed partial target must remain
            // correct. Own requests have already been checked before free return.
            if(e.paper<0)assert(!((view(p.order).display^e.color)&e.mask));
            count+=p.moves;state=std::move(p.order);
        }
        return double(count)/length;
    }
};
int main(int argc,char** argv){
    if(argc<2)return 2;int iterations=argc>2?std::stoi(argv[2]):1000,train=argc>3?std::stoi(argv[3]):1024,validation=argc>4?std::stoi(argv[4]):8192,width=argc>5?std::stoi(argv[5]):4;
    Model m(argv[1],width);m.potential_mode=argc>9?std::stoi(argv[9]):0;m.fast_insert=argc<=10||std::stoi(argv[10]);if(!m.update())return 3;auto start=std::chrono::steady_clock::now();auto elapsed=[&]{return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    auto original=m.op;double baseline=m.simulate(train,1000003),current=baseline,best=baseline;auto best_op=m.op;std::mt19937_64 rng(938361);int accepted=0;bool free_anchor=argc>8&&std::stoi(argv[8]);
    if(argc>6&&std::string(argv[6])!="-"){std::stringstream stream(argv[6]);std::string cell;std::vector<int> chosen;while(std::getline(stream,cell,','))chosen.push_back(std::stoi(cell));if(int(chosen.size())!=m.K)return 4;m.op=chosen;if(!m.update())return 5;current=best=m.simulate(train,1000003);best_op=chosen;}
    std::cerr<<"baseline "<<baseline<<" papers "<<m.K<<" sec "<<elapsed()<<'\n';
    for(int it=0;it<iterations;it++){
        int k=rng()%m.K,j=rng()%m.W;if((!free_anchor&&j==m.column[k])||!(m.allowed[k]>>j&1)||(m.op[k]^(1<<j))==0)continue;
        int old=m.op[k];m.op[k]^=1<<j;if(!m.update()){m.op[k]=old;m.update();continue;}
        double next=m.simulate(train,1000003),temp=.012*std::pow(.01,double(it)/std::max(1,iterations-1));
        if(next<=current||std::generate_canonical<double,53>(rng)<std::exp((current-next)/temp)){current=next;accepted++;if(current<best){best=current;best_op=m.op;std::cerr<<"best "<<it<<' '<<best<<" sec "<<elapsed()<<'\n';}}
        else{m.op[k]=old;m.update();}
    }
    std::uint64_t validation_seed=argc>7?std::stoull(argv[7]):200000003;
    m.op=original;m.update();double original_validation=m.simulate(validation,validation_seed);auto original_fallback=m.fallback_calls;
    m.op=best_op;m.update();double new_validation=m.simulate(validation,validation_seed);
    std::cout<<std::setprecision(12)<<"{\"papers\":"<<m.K<<",\"iterations\":"<<iterations<<",\"accepted\":"<<accepted<<",\"train_length\":"<<train<<",\"validation_length\":"<<validation<<",\"baseline_train\":"<<baseline<<",\"best_train\":"<<best<<",\"baseline_validation\":"<<original_validation<<",\"validation\":"<<new_validation<<",\"difference\":"<<new_validation-original_validation<<",\"original\":[";
    for(int k=0;k<m.K;k++)std::cout<<(k?",":"")<<original[k];std::cout<<"],\"opaque\":[";for(int k=0;k<m.K;k++)std::cout<<(k?",":"")<<best_op[k];std::cout<<"],\"fallback\":"<<m.fallback_calls<<",\"baseline_fallback\":"<<original_fallback<<",\"elapsed\":"<<elapsed()<<"}\n";
}
