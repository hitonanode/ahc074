from pathlib import Path
p=Path(__file__).resolve().parent;s=(p.parent/'triple-bound/design.hpp').read_text()
s=s.replace('double triple_price;Problem(const Design&d,double price)', 'double triple_price;U patch_mask=0,patch_color=0;int patch_handle=-1;double patch_fee=2;Problem(const Design&d,double price)')
s=s.replace('double fee=0;};','double fee=0;bool patched=false;};')
s=s.replace('std::vector<Group> groups;','std::vector<Group> groups;std::vector<int>alternate;')
needle='int id=groups.size();index[key(a,n)]=id;groups.push_back(g);if(n==2)pairs.push_back(id);if(n==3)triples.push_back(id);'
new='''int id=groups.size();index[key(a,n)]=id;groups.push_back(g);alternate.push_back(-1);if(n==2)pairs.push_back(id);if(n==3)triples.push_back(id);
        if(n==2&&p.patch_mask&&(g.diff&p.patch_mask)){
            U required=p.patch_mask|(1ULL<<p.patch_handle);int patched=-1;
            for(int t=0;t<2;t++)if(!((p.A[a[t]]^p.patch_color)&required))patched=t;
            if(patched>=0){Group q=g;q.patched=true;q.fee+=p.patch_fee;q.diff&=~p.patch_mask;q.a[0]=a[1-patched];q.a[1]=a[patched];int j=groups.size();alternate[id]=j;groups.push_back(q);alternate.push_back(id);pairs.push_back(j);}
        }'''
assert needle in s;s=s.replace(needle,new)
s=s.replace('Ucount(191-p.M)', 'Ucount(191-p.M-int(p.patch_mask!=0))')
s=s.replace('bool valid(int id,int col)const{return !(groups[id].diff>>handles[col]&1);}', '''bool valid(int id,int col)const{
        if(groups[id].patched){int h=std::find(handles.begin(),handles.begin()+H,p.patch_handle)-handles.begin();if(col>=h)return false;}
        return !(groups[id].diff>>handles[col]&1);
    }''')
old='''int a=rng()%H,b=rng()%H;if(a==b)continue;bool ok=true;
                for(auto u:units)if((u.column==a&&!valid(u.group,b))||(u.column==b&&!valid(u.group,a))){ok=false;break;}if(!ok)continue;
                std::swap(handles[a],handles[b]);for(auto&u:units){if(u.column==a)u.column=b;else if(u.column==b)u.column=a;}rebuild();'''
new='''int a=rng()%H,b=rng()%H;if(a==b)continue;
                std::swap(handles[a],handles[b]);for(auto&u:units){if(u.column==a)u.column=b;else if(u.column==b)u.column=a;}
                bool ok=true;for(auto u:units)if(!valid(u.group,u.column))ok=false;
                if(!ok){std::swap(handles[a],handles[b]);for(auto&u:units){if(u.column==a)u.column=b;else if(u.column==b)u.column=a;}continue;}
                rebuild();'''
assert old in s;s=s.replace(old,new)
old='if(kind<40){if(kind<22)nx.column=rng()%H;else std::swap(nx.column,ny.column);}'
new='''if(kind<12){if(alternate[nx.group]<0)continue;nx.group=alternate[nx.group];}
                else if(kind<40){if(kind<26)nx.column=rng()%H;else std::swap(nx.column,ny.column);}'''
assert old in s;s=s.replace(old,new)
old='nx.group=lookup(a,cut);ny.group=lookup(b,n-cut);if(nx.group<0||ny.group<0)continue;'
new='''nx.group=lookup(a,cut);ny.group=lookup(b,n-cut);if(nx.group<0||ny.group<0)continue;
                    if(alternate[nx.group]>=0&&(rng()&1))nx.group=alternate[nx.group];
                    if(alternate[ny.group]>=0&&(rng()&1))ny.group=alternate[ny.group];'''
assert old in s;s=s.replace(old,new)
s=s.replace('double patch_fee=2;Problem(', 'double patch_fee=2;std::vector<int> initial_handles;Problem(')
s=s.replace('triple_price(price){', 'triple_price(price),initial_handles(d.handle){')
s=s.replace('for(int j=0;j<H;j++)handles[j]=p.G+j;', 'for(int j=0;j<H;j++)handles[j]=p.initial_handles[j];')
s=s.replace('if(col>=h)return false;', 'if(col>=h)return false;for(int j=0;j<H;j++)if((p.patch_mask>>handles[j]&1)&&j>col)return false;')
s=s.replace('bool ok=true;for(auto u:units)if(!valid(u.group,u.column))ok=false;', 'bool ok=true;for(auto u:units)if(!valid(u.group,u.column))ok=false;if(p.patch_mask){int h=std::find(handles.begin(),handles.begin()+H,p.patch_handle)-handles.begin();for(int j=h;j<H;j++)if(p.patch_mask>>handles[j]&1)ok=false;}')
(p/'design.hpp').write_text(s)
