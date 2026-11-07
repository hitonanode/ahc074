from make_quality import base,write
for tag,settings in [('reqrepeat05',{'REPEAT_MIN':'.05'}),('reqrepeat10',{'REPEAT_MIN':'.10'}),('reqround1',{'NS_ROUNDS':'1'})]:
 extra='        if(const char* explicit_value=std::getenv(local.c_str()))return explicit_value;\n'
 for k,v in settings.items():extra+=f'        if(std::strcmp(name,"{k}")==0)return "{v}";\n'
 s=base.replace('        return std::getenv(local.c_str());',extra+'        return nullptr;',1)
 write('deval-'+tag,s,'注文探索の既定設定だけを変更: '+str(settings)+'。設計段は変更しない。')
