#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

using U=std::uint64_t;
struct Word {
    U code=1;
    std::array<unsigned char,32> text{};
    unsigned char length=0;
    std::vector<int> children,suffix;
};
struct Queue {
    std::array<int,4> counts;
    int N=0;
    double r0,r1,total;
    std::vector<Word> words;
    std::vector<std::vector<int>> levels;
    std::vector<int> states,full_index;
    std::unordered_map<U,int> index;
    std::vector<double> h,th;
    std::vector<std::array<double,5>> minimum;
    std::vector<std::vector<int>> greedy_next;
    std::vector<std::vector<int>> greedy_cost;
    Queue(std::array<int,4> c,double a,double b):counts(c),r0(a),r1(b) {
        N=std::accumulate(c.begin(),c.end(),0);assert(N<=30);levels.resize(N+1);
        total=r0+r1;for(int k=0;k<4;k++)total+=(1+(k>>1))*counts[k];
        std::array<int,4> used{};Word empty;generate(empty,used);
        full_index.assign(words.size(),-1);states=levels[N];
        for(int i=0;i<int(states.size());i++)full_index[states[i]]=i;
        for(auto& w:words) {
            const int L=w.length;
            for(int p=0;p<L;p++) {
                U key=1;for(int j=0;j<L;j++)if(j!=p)key=(key<<2)|w.text[j];
                int id=index.at(key);if(std::find(w.children.begin(),w.children.end(),id)==w.children.end())w.children.push_back(id);
            }
            if(L==N)for(int p=0;p<=N;p++) {
                U key=1;for(int j=p;j<N;j++)key=(key<<2)|w.text[j];w.suffix.push_back(index.at(key));
            }
        }
        h.resize(states.size());th.resize(states.size());minimum.resize(words.size());
    }
    void generate(Word w,std::array<int,4>& used) {
        int id=words.size();index[w.code]=id;words.push_back(w);levels[w.length].push_back(id);
        for(int k=0;k<4;k++)if(used[k]<counts[k]) {
            auto next=w;next.code=(next.code<<2)|k;next.text[next.length++]=k;used[k]++;generate(next,used);used[k]--;
        }
    }
    void minima() {
        const double inf=1e100;for(auto& v:minimum)v.fill(inf);
        for(int s=0;s<int(states.size());s++) {
            int id=states[s];auto& w=words[id];minimum[id][0]=h[s];
            minimum[w.suffix[1]][1+w.text[0]]=std::min(minimum[w.suffix[1]][1+w.text[0]],h[s]);
        }
        // minimum[word][0] is min h over full strings containing word. The
        // remaining four entries additionally fix the full string's first type,
        // and search only in its tail. Deleting a letter preserves containment.
        for(int len=N;len>0;len--)for(int id:levels[len]) {
            auto v=minimum[id];for(int child:words[id].children)for(int k=0;k<5;k++)minimum[child][k]=std::min(minimum[child][k],v[k]);
        }
    }
    void step_optimal() {
        minima();
        for(int s=0;s<int(states.size());s++) {
            auto& w=words[states[s]];double result=0;std::array<double,2> color{1e100,1e100};
            for(int d=0;d<N;d++) {
                int type=w.text[d],suffix=w.suffix[d+1],weight=1+(type>>1);
                result+=weight*(d+minimum[suffix][0]);
                color[type&1]=std::min(color[type&1],d+minimum[suffix][type+1]);
            }
            result+=r0*color[0]+r1*color[1];th[s]=result/total;
        }
    }
    double phi(const std::vector<int>& row) const {
        double value=0;int first[2]={N,N};
        for(int d=0;d<int(row.size());d++){int k=row[d];value+=(1+(k>>1))*d;first[k&1]=std::min(first[k&1],d);}
        return value+r0*first[0]+r1*first[1];
    }
    void greedy_insert(std::vector<int>& row,int type,int low) const {
        double best=1e100;int chosen=row.size();
        for(int d=low;d<=int(row.size());d++) {
            auto test=row;test.insert(test.begin()+d,type);double cost=phi(test);
            if(cost<=best+1e-10){best=cost;chosen=d;}
        }
        row.insert(row.begin()+chosen,type);
    }
    int greedy_transition(const Word& w,int requested,bool own) const {
        std::vector<int> row(w.text.begin(),w.text.begin()+N);int marker=requested;
        while(marker>0) {
            int top=row.front();row.erase(row.begin());marker--;
            greedy_insert(row,top,marker+1);
        }
        if(own){int top=row.front();row.erase(row.begin());greedy_insert(row,top,0);}
        U key=1;for(int x:row)key=(key<<2)|x;return full_index[index.at(key)];
    }
    void prepare_greedy() {
        greedy_next.assign(states.size(),std::vector<int>(N+2));greedy_cost=greedy_next;
        for(int s=0;s<int(states.size());s++) {
            auto& w=words[states[s]];
            for(int d=0;d<N;d++){greedy_next[s][d]=greedy_transition(w,d,true);greedy_cost[s][d]=d;}
            for(int color=0;color<2;color++) {
                int d=0;while((w.text[d]&1)!=color)d++;
                greedy_next[s][N+color]=greedy_transition(w,d,false);greedy_cost[s][N+color]=d;
            }
        }
    }
    void step_greedy() {
        for(int s=0;s<int(states.size());s++) {
            auto& w=words[states[s]];double result=0;
            for(int d=0;d<N;d++)result+=(1+(w.text[d]>>1))*(greedy_cost[s][d]+h[greedy_next[s][d]]);
            result+=r0*(greedy_cost[s][N]+h[greedy_next[s][N]]);
            result+=r1*(greedy_cost[s][N+1]+h[greedy_next[s][N+1]]);th[s]=result/total;
        }
    }
    struct Value {double lower,upper;int iterations;};
    Value solve(bool optimal,int limit=1000) {
        std::fill(h.begin(),h.end(),0);Value result{};
        for(int it=0;it<limit;it++) {
            if(optimal)step_optimal();else step_greedy();
            double lo=1e100,hi=-1e100,mean=0;
            for(int s=0;s<int(h.size());s++){lo=std::min(lo,th[s]-h[s]);hi=std::max(hi,th[s]-h[s]);mean+=th[s];}
            mean/=h.size();for(int s=0;s<int(h.size());s++)h[s]=.3*h[s]+.7*(th[s]-mean);
            result={lo,hi,it+1};if(hi-lo<1e-9)break;
        }
        return result;
    }
};
int main(int argc,char** argv) {
    auto t0=std::chrono::steady_clock::now();std::array<int,4> counts{2,2,1,1};double r0=20,r1=10;
    for(int i=1;i<argc;i++) {
        std::string s=argv[i];auto p=s.find('=');if(p==s.npos)continue;auto k=s.substr(0,p),v=s.substr(p+1);
        if(k=="counts"){std::replace(v.begin(),v.end(),',',' ');std::istringstream in(v);for(int& x:counts)in>>x;}
        else if(k=="r0")r0=std::stod(v);else if(k=="r1")r1=std::stod(v);
    }
    if(counts[0]+counts[2]==0||counts[1]+counts[3]==0)return 2;
    Queue q(counts,r0,r1);q.prepare_greedy();auto greedy=q.solve(false),optimal=q.solve(true);
    std::cout<<std::setprecision(12)<<"{\"counts\":["<<counts[0]<<','<<counts[1]<<','<<counts[2]<<','<<counts[3]<<"],\"r0\":"<<r0<<",\"r1\":"<<r1
        <<",\"words\":"<<q.words.size()<<",\"states\":"<<q.states.size()<<",\"greedy_lo\":"<<greedy.lower<<",\"greedy_hi\":"<<greedy.upper<<",\"optimal_lo\":"<<optimal.lower<<",\"optimal_hi\":"<<optimal.upper
        <<",\"difference\":"<<(optimal.lower+optimal.upper-greedy.lower-greedy.upper)/2<<",\"global_difference\":"<<(optimal.lower+optimal.upper-greedy.lower-greedy.upper)/2*q.total/256
        <<",\"iterations\":"<<optimal.iterations<<",\"elapsed\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count()*CLOCK_SCALE<<"}\n";
}
