#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

using U64=std::uint64_t;
struct Paper{U64 op=0,black=0;};
struct Query{int need=0,color=0;double prob=0;};
struct Result{std::vector<double> value;std::vector<int> goal,steps;};
struct Model{
    static constexpr int S=720;
    std::array<int,6> mask{},color{};
    std::vector<std::array<int,6>> perm;
    std::array<std::vector<std::vector<int>>,8> reverse;
    std::vector<int> display;
    std::vector<Query> query;
    std::vector<double> approximate;
    double used=0, independent=0;
    static int encode(const std::array<int,6>&p){int z=0;for(int i=0;i<6;++i)z|=p[i]<<(3*i);return z;}
    Model(const std::array<int,6>&m,const std::array<int,6>&b,
          const std::array<double,27>&d):mask(m),color(b){
        std::array<int,6>p{0,1,2,3,4,5};
        std::vector<int>index(1<<18,-1);
        do{index[encode(p)]=perm.size();perm.push_back(p);}while(std::next_permutation(p.begin(),p.end()));
        assert(perm.size()==S);
        display.resize(S);approximate.assign(S,0);
        double request[3][2]{};
        for(int z=1;z<27;++z)if(d[z]){
            Query q;int v=z;for(int j=0;j<3;++j){int c=v%3;v/=3;
                if(c){q.need|=1<<j;q.color|=(c-1)<<j;request[j][c-1]+=d[z];}}
            q.prob=d[z];query.push_back(q);used+=d[z];
        }
        for(int j=0;j<3;++j){double a=request[j][0],b=request[j][1];if(a+b)independent+=2*a*b/(a+b);}
        for(auto&q:query)q.prob/=used;
        for(int need=1;need<8;++need)reverse[need].resize(S);
        for(int s=0;s<S;++s){int covered=0;
            for(int k:perm[s]){int owns=mask[k]&~covered;display[s]|=color[k]&owns;covered|=mask[k];}
            assert(covered==7);
            for(int j=0;j<3;++j)for(int b=0;b<2;++b){int n=0;
                for(int k:perm[s])if(mask[k]>>j&1){if((color[k]>>j&1)==b)break;++n;}
                approximate[s]+=request[j][b]*n;
            }
            for(int need=1;need<8;++need){covered=0;
                for(int from=0;from<6;++from){int k=perm[s][from];int owns=mask[k]&need&~covered;
                    covered|=mask[k];if(!owns)continue;
                    for(int to=0;to<6;++to)if(to!=from){auto a=perm[s];
                        if(from<to)for(int i=from;i<to;++i)a[i]=a[i+1];
                        else for(int i=from;i>to;--i)a[i]=a[i-1];a[to]=k;
                        int t=index[encode(a)];assert(t>=0);reverse[need][t].push_back(s);
                    }
                }
            }
        }
        for(int need=1;need<8;++need)for(auto&v:reverse[need]){
            std::sort(v.begin(),v.end());v.erase(std::unique(v.begin(),v.end()),v.end());
        }
    }
    Result solve_query(const Query&q,const std::vector<double>&h)const{
        Result r;r.value.assign(S,1e100);r.goal.assign(S,-1);r.steps.assign(S,0);
        using Item=std::pair<double,int>;
        std::priority_queue<Item,std::vector<Item>,std::greater<Item>>pq;
        for(int s=0;s<S;++s)if(((display[s]^q.color)&q.need)==0){r.value[s]=h[s];r.goal[s]=s;pq.emplace(h[s],s);}
        while(!pq.empty()){auto[d,s]=pq.top();pq.pop();if(d!=r.value[s])continue;
            for(int t:reverse[q.need][s])if(d+1<r.value[t]-1e-12){
                r.value[t]=d+1;r.goal[t]=r.goal[s];r.steps[t]=r.steps[s]+1;pq.emplace(d+1,t);
            }
        }
        for(int s=0;s<S;++s)assert(r.goal[s]>=0);
        return r;
    }
    std::vector<double>bellman(const std::vector<double>&h)const{
        std::vector<double>r(S,0);for(auto&q:query){auto a=solve_query(q,h);
            for(int s=0;s<S;++s)r[s]+=q.prob*a.value[s];}return r;
    }
    double evaluate_terminal(const std::vector<double>&h)const{
        std::vector<Result>policy;for(auto&q:query)policy.push_back(solve_query(q,h));
        // Start every compared policy in the same canonical column order. Laziness
        // removes periodicity without changing its stationary average cost.
        std::vector<double>p(S,0),next(S);p[0]=1;
        for(int it=0;it<10000;++it){
            for(int s=0;s<S;++s)next[s]=p[s]*0.5;
            for(int t=0;t<(int)query.size();++t)for(int s=0;s<S;++s)
                next[policy[t].goal[s]]+=p[s]*query[t].prob*0.5;
            double diff=0;for(int s=0;s<S;++s)diff+=std::abs(next[s]-p[s]);
            p.swap(next);if(diff<1e-13)break;
        }
        double c=0;for(int t=0;t<(int)query.size();++t)for(int s=0;s<S;++s)
            c+=p[s]*query[t].prob*policy[t].steps[s];
        return c*used;
    }
    double evaluate_policy(double multiplier)const{
        std::vector<double>h=approximate;for(double&x:h)x*=multiplier;
        return evaluate_terminal(h);
    }
    std::vector<std::vector<double>> features()const{
        // 1 intercept, 26 exact partial-query distances, 6 color depths,
        // and the number of currently visible papers.
        std::vector<std::vector<double>>f(S,std::vector<double>(34,1));
        for(int z=1;z<27;++z){Query q;int v=z;
            for(int j=0;j<3;++j){int c=v%3;v/=3;if(c){q.need|=1<<j;q.color|=(c-1)<<j;}}
            auto r=solve_query(q,std::vector<double>(S));
            for(int s=0;s<S;++s)f[s][z]=r.steps[s];
        }
        for(int s=0;s<S;++s){
            for(int j=0;j<3;++j)for(int b=0;b<2;++b){int depth=0;
                for(int k:perm[s])if(mask[k]>>j&1){if((color[k]>>j&1)==b)break;++depth;}
                f[s][27+2*j+b]=depth;
            }
            int covered=0,n=0;for(int k:perm[s]){n+=bool(mask[k]&~covered);covered|=mask[k];}f[s][33]=n;
        }
        return f;
    }
    static bool held_out(int s){return (std::uint32_t(s)*2654435761U)%5==0;}
    void regression(int group,const std::vector<double>&h,const std::vector<std::vector<double>>&f,int columns)const{
        std::vector<std::vector<double>>a(columns,std::vector<double>(columns+1));
        for(int s=0;s<S;++s)if(!held_out(s))for(int i=0;i<columns;++i){
            for(int j=0;j<columns;++j)a[i][j]+=f[s][i]*f[s][j];a[i][columns]+=f[s][i]*h[s];
        }
        for(int i=1;i<columns;++i)a[i][i]+=1e-7;
        for(int i=0;i<columns;++i){int p=i;for(int j=i+1;j<columns;++j)if(std::abs(a[j][i])>std::abs(a[p][i]))p=j;
            std::swap(a[i],a[p]);assert(std::abs(a[i][i])>1e-12);double d=a[i][i];
            for(int j=i;j<=columns;++j)a[i][j]/=d;
            for(int k=0;k<columns;++k)if(k!=i){double v=a[k][i];for(int j=i;j<=columns;++j)a[k][j]-=v*a[i][j];}
        }
        std::vector<double>prediction(S);
        for(int s=0;s<S;++s)for(int i=0;i<columns;++i)prediction[s]+=a[i][columns]*f[s][i];
        double mean=0,n=0;for(int s=0;s<S;++s)if(held_out(s)){mean+=h[s];n++;}mean/=n;
        double err=0,var=0;for(int s=0;s<S;++s)if(held_out(s)){err+=std::pow(prediction[s]-h[s],2);var+=std::pow(h[s]-mean,2);}
        std::cout<<"regression_group="<<group<<" features="<<columns-1<<" held_out="<<int(n)
                 <<" test_r2="<<(var?1-err/var:1)<<" test_rmse="<<std::sqrt(err/n)
                 <<" stationary_cost="<<evaluate_terminal(prediction)<<" coefficients=";
        for(int i=0;i<columns;++i)std::cout<<(i?",":"")<<a[i][columns];std::cout<<"\n";
    }
    std::vector<double> run(int group,int iterations)const{
        if(used==0){std::cout<<"group="<<group<<" unused=1\n";return std::vector<double>(S);}
        std::vector<double>h(S,0);double lo=0,hi=0;int it=0;
        for(;it<iterations;++it){auto t=bellman(h);lo=1e100;hi=-1e100;
            for(int s=0;s<S;++s){double d=t[s]-h[s];lo=std::min(lo,d);hi=std::max(hi,d);}
            if(hi-lo<1e-9)break;
            double ref=(h[0]+t[0])*0.5;
            for(int s=0;s<S;++s)h[s]=(h[s]+t[s])*0.5-ref;
        }
        double mh=std::accumulate(h.begin(),h.end(),0.0)/S;
        double mf=std::accumulate(approximate.begin(),approximate.end(),0.0)/S;
        double cov=0,vh=0,vf=0;
        for(int s=0;s<S;++s){double a=h[s]-mh,b=approximate[s]-mf;cov+=a*b;vh+=a*a;vf+=b*b;}
        std::cout<<std::setprecision(9)<<"group="<<group<<" used="<<used<<" independent="<<independent
            <<" optimal_low="<<lo*used<<" optimal_high="<<hi*used<<" iterations="<<it
            <<" bias_approx_slope="<<(vf?cov/vf:0)<<" bias_approx_correlation="<<(vh*vf?cov/std::sqrt(vh*vf):0)
            <<" policy_tie="<<evaluate_policy(1e-7)<<" policy_w1="<<evaluate_policy(1)
            <<" policy_w4="<<evaluate_policy(4)<<" policy_normalized="<<evaluate_policy(1/used)<<"\n";
        auto joint=bellman(std::vector<double>(S));auto joint_tie=joint;
        for(double&v:joint_tie)v*=1e-7;
        std::cout<<"joint_policy_group="<<group<<" joint_one_step="<<evaluate_terminal(joint)
                 <<" shortest_then_joint="<<evaluate_terminal(joint_tie)<<"\n";
        if(std::getenv("MDP_REGRESSION")){
            auto f=features();regression(group,h,f,27);regression(group,h,f,34);
            auto tie=h;for(double&v:tie)v*=1e-7;
            std::cout<<"bias_policy_group="<<group<<" exact_h="<<evaluate_terminal(h)
                     <<" shortest_then_h="<<evaluate_terminal(tie)<<"\n";
        }
        return h;
    }
};

void cross_fit(const std::vector<Model>&models,const std::vector<std::vector<double>>&bias){
    constexpr int D=8,S=720;
    int G=models.size();
    std::vector<std::vector<std::array<double,D>>>f(G,std::vector<std::array<double,D>>(S));
    std::vector<std::array<double,D>>mean(G);
    std::vector<double>mh(G);
    for(int g=0;g<G;++g){auto raw=models[g].features();
        for(int s=0;s<S;++s)for(auto&q:models[g].query){
            for(int subset=q.need;subset;subset=(subset-1)&q.need){
                int z=0,p=1;for(int j=0;j<3;++j){if(subset>>j&1)z+=p*(1+(q.color>>j&1));p*=3;}
                f[g][s][subset-1]+=q.prob*raw[s][z];
            }
            int z=0,p=1;for(int j=0;j<3;++j){if(q.need>>j&1)z+=p*(1+(q.color>>j&1));p*=3;}
            f[g][s][7]+=q.prob*raw[s][z];
        }
        for(int s=0;s<S;++s){mh[g]+=bias[g][s]/S;for(int j=0;j<D;++j)mean[g][j]+=f[g][s][j]/S;}
    }
    for(int held=0;held<G;++held){
        double a[D][D+1]{};
        for(int g=0;g<G;++g)if(g!=held)for(int s=0;s<S;++s)for(int i=0;i<D;++i){
            double x=f[g][s][i]-mean[g][i];
            for(int j=0;j<D;++j)a[i][j]+=x*(f[g][s][j]-mean[g][j]);
            a[i][D]+=x*(bias[g][s]-mh[g]);
        }
        for(int i=0;i<D;++i)a[i][i]+=1e-7;
        for(int i=0;i<D;++i){int p=i;for(int j=i+1;j<D;++j)if(std::abs(a[j][i])>std::abs(a[p][i]))p=j;
            for(int j=0;j<=D;++j)std::swap(a[i][j],a[p][j]);
            assert(std::abs(a[i][i])>1e-12);double v=a[i][i];for(int j=i;j<=D;++j)a[i][j]/=v;
            for(int k=0;k<D;++k)if(k!=i){v=a[k][i];for(int j=i;j<=D;++j)a[k][j]-=v*a[i][j];}
        }
        std::vector<double>prediction(S);double err=0,var=0;
        for(int s=0;s<S;++s){for(int i=0;i<D;++i)prediction[s]+=a[i][D]*(f[held][s][i]-mean[held][i]);
            double truth=bias[held][s]-mh[held];err+=std::pow(prediction[s]-truth,2);var+=truth*truth;
        }
        std::cout<<"cross_group="<<held<<" features=8 train_groups="<<G-1
                 <<" test_r2="<<(var?1-err/var:1)<<" test_rmse="<<std::sqrt(err/S)
                 <<" stationary_cost="<<models[held].evaluate_terminal(prediction)<<" coefficients=";
        for(int i=0;i<D;++i)std::cout<<(i?",":"")<<a[i][D];std::cout<<"\n";
    }
}
int main(int argc,char**argv){
    if(argc==2 && std::string(argv[1])=="--self-test"){
        // Three completely independent white/black pairs have exactly one move
        // per differing required bit. Under full uniform requests the optimum
        // must be 3/2, in every one of the 720 states.
        std::array<int,6>m{1,1,2,2,4,4},b{0,1,0,2,0,4};
        std::array<double,27>d{};for(int x=0;x<8;++x){int z=0,p=1;
            for(int j=0;j<3;++j){z+=p*(1+(x>>j&1));p*=3;}d[z]=0.125;}
        Model model(m,b,d);auto v=model.bellman(std::vector<double>(720));
        for(double x:v)assert(std::abs(x-1.5)<1e-12);
        std::cout<<"independent_pairs_720_states=passed expected_cost=1.5\n";return 0;
    }
    if(argc>=3 && (std::string(argv[1])=="--models" || std::string(argv[1])=="--cross-models")){
        std::ifstream f(argv[2]);int groups;f>>groups;assert(f&&groups>0);
        int iterations=argc>3?std::atoi(argv[3]):400;
        std::vector<Model>models;std::vector<std::vector<double>>bias;
        for(int i=0;i<groups;++i){int g;std::array<int,6>m{},b{};std::array<double,27>d{};
            f>>g;for(int&v:m)f>>v;for(int&v:b)f>>v;for(double&v:d){f>>v;v/=256;}
            assert(f);models.emplace_back(m,b,d);bias.push_back(models.back().run(g,iterations));
        }
        if(std::string(argv[1])=="--cross-models")cross_fit(models,bias);
        return 0;
    }
    if(argc<3){std::cerr<<"usage: block_mdp input.txt output.txt [iterations]\n";return 2;}
    std::ifstream input(argv[1]),output(argv[2]);int N,K,P,R;input>>N>>K>>P>>R;
    assert(input&&output&&N==64&&K==192&&P==256);
    std::vector<U64>A(P);for(auto&x:A){std::string s;input>>s;assert(s.size()==64);for(int j=0;j<64;++j)if(s[j]=='1')x|=1ULL<<j;}
    std::vector<Paper>paper(K);for(auto&p:paper){std::string s;output>>s;assert(s.size()==64);
        for(int j=0;j<64;++j){if(s[j]!='.')p.op|=1ULL<<j;if(s[j]=='1')p.black|=1ULL<<j;}}
    U64 generic=0;for(int k=0;k<6;++k)generic|=paper[k].op;
    std::vector<std::pair<int,int>>starts;
    for(int j=0;j<64;++j)if(!(generic>>j&1)){int first=-1;for(int k=6;k<K;++k)if(paper[k].op>>j&1){first=k;break;}
        assert(first>=0);starts.emplace_back(first,j);}
    std::sort(starts.begin(),starts.end());for(int c=1;c<(int)starts.size();++c)assert(starts[c-1].first<starts[c].first);
    std::vector<int>ded(P);int ambiguous=0;
    for(int u=0;u<P;++u){int n=0;for(int k=6;k<K;++k)if(((A[u]^paper[k].black)&paper[k].op)==0){ded[u]=k;++n;}
        assert(n>0);ambiguous+=n>1;}
    if(ambiguous){std::cerr<<"ambiguous dedicated identities="<<ambiguous<<"; refusing approximate ownership\n";return 3;}
    std::cout<<"input="<<argv[1]<<" design="<<argv[2]<<" handles="<<starts.size()<<" ownership=unique\n";
    int iterations=argc>3?std::atoi(argv[3]):400;
    for(int g=0;g+3<=(int)starts.size();g+=3){
        std::array<int,6>m{},b{};std::array<double,27>d{};
        for(int c=0;c<3;++c)for(int v=0;v<2;++v){int choose=-1;
            int begin=starts[g+c].first,end=g+c+1<(int)starts.size()?starts[g+c+1].first:K;
            for(int k=begin;k<end;++k)if(((paper[k].black>>starts[g+c].second)&1)==v){choose=k;break;}
            assert(choose>=0);for(int j=0;j<3;++j){m[2*c+v]|=((paper[choose].op>>starts[g+j].second)&1)<<j;
                b[2*c+v]|=((paper[choose].black>>starts[g+j].second)&1)<<j;}
        }
        for(int u=0;u<P;++u){int z=0,base=1;for(int j=0;j<3;++j){int w=starts[g+j].second;
                if(!(paper[ded[u]].op>>w&1))z+=base*(1+((A[u]>>w)&1));base*=3;}d[z]+=1.0/P;}
        Model model(m,b,d);model.run(g/3,iterations);
    }
}
