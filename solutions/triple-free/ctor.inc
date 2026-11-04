  std::ifstream in(path);int p,n;in>>p>>n;assert(p==256);
  for(auto&a:A)in>>a;
  for(int i=0;i<n;i++){Group x;int size;in>>size;x.targets.resize(size);for(int&t:x.targets)in>>t;groups.push_back(x);}
  assert(in);
  if(triple_limit>=0){
   int nt=0;for(auto&x:groups)nt+=x.targets.size()==3;
   while(nt>triple_limit){
    int chosen=-1,largest=-1;
    for(int i=0;i<int(groups.size());i++)if(groups[i].targets.size()==3){
     auto t=groups[i].targets;int d=std::popcount((A[t[0]]^A[t[1]])|(A[t[0]]^A[t[2]]));
     if(d>largest)largest=d,chosen=i;
    }
    auto t=groups[chosen].targets;int a=0,b=1,distance=100;
    for(int i=0;i<3;i++)for(int j=i+1;j<3;j++)if(std::popcount(A[t[i]]^A[t[j]])<distance)distance=std::popcount(A[t[i]]^A[t[j]]),a=i,b=j;
    groups[chosen].targets={t[a],t[b]};groups.push_back(Group{{t[3-a-b]},0});nt--;
   }
  }
  // Two additional generic papers require two additional merges compared with
  // the six-paper seed. Choose close remaining singletons for these pairs.
  while(int(groups.size())>191-M){
   int a=-1,b=-1,bd=100;
   for(int i=0;i<int(groups.size());i++)if(groups[i].targets.size()==1)
    for(int j=i+1;j<int(groups.size());j++)if(groups[j].targets.size()==1){
     int d=std::popcount(A[groups[i].targets[0]]^A[groups[j].targets[0]]);
     if(d<bd)bd=d,a=i,b=j;
    }
   assert(a>=0);groups[a].targets.push_back(groups[b].targets[0]);groups.erase(groups.begin()+b);
  }
