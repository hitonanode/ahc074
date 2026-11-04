#include "design.hpp"

int main(int argc,char**argv){
    if(argc<3)return 2;auto raw=head::load(argv[1],argv[2]);if(!raw)return 3;
    auto d=recover(*raw);d->refresh_reset();
    int iterations=argc>3?std::stoi(argv[3]):5000000;
    double reference=0;std::cout<<std::setprecision(12)<<"[";
    std::vector<double> prices={-1,2.5,3,3.5,4};
    for(int p=0;p<int(prices.size());p++){
        double begin=elapsed_sec();Problem problem(*d,prices[p]);Search search(problem);
        for(int c=0;c<d->H;c++)search.handles[c]=d->handle[c];
        for(auto u:d->unit){int id=search.lookup({u.a,u.b,-1},u.b>=0?2:1);assert(id>=0);search.units.push_back({id,u.c});}
        search.rebuild();search.refresh();assert(std::abs(search.current-d->cur)<1e-5);
        search.optimize(iterations);
        double cols=0,holes=0,generic=0;int triples=0,pairs=0;
        for(int c=0;c<search.H;c++){cols+=Search::colcost(search.counts[c]);holes+=search.holecost(c);}
        for(auto u:search.units){auto&v=search.groups[u.group];generic+=v.fee;triples+=v.n==3;pairs+=v.n==2;}
        assert(std::abs(cols+holes+generic-search.current)<1e-5);
        double value=search.current/256;if(!p)reference=value;
        if(argc>4 && prices[p]==3.5){
            std::ofstream out(argv[4]);out<<256<<' '<<search.Ucount<<'\n';
            for(auto a:problem.A)out<<a<<'\n';
            for(auto u:search.units){auto g=search.groups[u.group];out<<g.n;for(int i=0;i<g.n;i++)out<<' '<<g.a[i];out<<'\n';}
        }
        std::cout<<(p?",":"")<<"{\"price\":"<<prices[p]<<",\"model\":"<<value<<",\"difference\":"<<value-reference<<",\"columns\":"<<cols/256<<",\"holes\":"<<holes/256<<",\"generic\":"<<generic/256<<",\"triples\":"<<triples<<",\"pairs\":"<<pairs<<",\"catalog\":"<<search.triples.size()<<",\"seconds\":"<<elapsed_sec()-begin<<"}"<<std::flush;
    }
    std::cout<<"]\n";
}
