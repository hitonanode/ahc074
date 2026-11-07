from experiment import run
for tag in ['screen2','screen1','climb25','match1']:
    run(tag,'solutions/deval-'+tag,{},'0-500')
