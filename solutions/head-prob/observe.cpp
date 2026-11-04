#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "../anchor-match/head.hpp"
int main(int argc,char**argv){auto raw=head::load(argv[1],argv[2]);auto d=recover(*raw);Solver s=*raw;materialize(s,*d);HeadModel h(*d);
 std::vector<double>ones(d->H),counts(d->H),best(d->H);std::mt19937_64 rng(908715231);int prev=rng()%P;
 for(int t=0;t<8192;t++){
  if(t>=512){std::vector<bool>seen(d->H);for(int k:s.order){int c=s.col_of[k];if(c<0||k==s.top_d||s.is_filler(k)||seen[c])continue;seen[c]=true;counts[c]++;ones[c]+=s.h_blk[k]>>c&1;best[c]+=h.beta[k-7]>0;}}
  int u=int(rng()%(P-1));if(u>=prev)u++;prev=u;s.process(u);
 }
 std::cout<<std::setprecision(12)<<"[";
 for(int c=0;c<d->H;c++){double x=d->hn[c][0],y=d->hn[c][1],r=2*d->nt[c];std::cout<<(c?",":"")<<"{\"column\":"<<c<<",\"n0\":"<<x<<",\"n1\":"<<y<<",\"targets\":"<<d->nt[c]<<",\"samples\":"<<counts[c]<<",\"actual\":"<<ones[c]/counts[c]<<",\"original\":"<<y/(x+y)<<",\"reset\":"<<(y+r*(y>x))/(x+y+r)<<",\"best_share\":"<<best[c]/counts[c]<<"}";}
 std::cout<<"]\n";
}
