from experiment import run
for name in ['mapcold','mapstall128']:
 run(name,'solutions/deval-'+name,{'DESIGN_FROM':'20261107-073610_deval-'+name},'0-500')
