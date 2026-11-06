#define main ng_product_entrypoint
#include "ng_product_cover.cpp"
#undef main
int main(){if(::setenv("NG_G","0",1)!=0)return 13;return ng_product_entrypoint();}
