
int main(int argc,char**argv){
 if(argc<2)return 2;int iterations=argc>2?std::stoi(argv[2]):10000000;
 auto start=std::chrono::steady_clock::now();Problem p(argv[1]);std::cout<<std::setprecision(12)<<"[";
 for(int q=0;q<2;q++){
  Search search(p);bool ok=search.initialize(q?25:0);
  if(!ok){std::cout<<(q?",":"")<<"{\"failed\":true}";continue;}
  search.refresh();search.optimize(iterations);
  int triples=0,pairs=0;double cols=0,holes=0,generic=0;
  for(auto u:search.units){auto&v=search.groups[u.group];triples+=v.n==3;pairs+=v.n==2;generic+=v.fee;}
  for(int c=0;c<search.H;c++){cols+=Search::colcost(search.counts[c]);holes+=search.holecost(c);}
  assert(std::abs(cols+holes+generic-search.current)<1e-5);
  std::cout<<(q?",":"")<<"{\"M\":"<<p.M<<",\"G\":"<<p.G<<",\"complete\":"<<p.complete<<",\"initial_triples\":"<<(q?25:0)<<",\"catalog\":"<<search.triples.size()<<",\"cost\":"<<search.current/256<<",\"columns\":"<<cols/256<<",\"holes\":"<<holes/256<<",\"generic\":"<<generic/256<<",\"triples\":"<<triples<<",\"pairs\":"<<pairs<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
