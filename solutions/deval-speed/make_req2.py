from make_quality import base,write
for tag,settings in [
    ('reqmode2',{'MODE':2}),
    ('reqinterior4',{'NS_INTERIOR':4}),
    ('reqshort1',{'NS_SHORT_ROUNDS':1}),
    ('reqrefine1',{'REFINE_BEST':1}),
    ('reqwidth4',{'NEUTRAL_WIDTH':4}),
]:
    extra='        if(const char* explicit_value=std::getenv(local.c_str()))return explicit_value;\n'
    for k,v in settings.items():extra+=f'        if(std::strcmp(name,"{k}")==0)return "{v}";\n'
    s=base.replace('        return std::getenv(local.c_str());',extra+'        return nullptr;',1)
    write('deval-'+tag,s,'注文探索の既定設定だけを変更: '+str(settings)+'。設計段は変更しない。')
