from pathlib import Path
p=Path(__file__).resolve().parent;s=(p.parent/'reset-head/main.cpp').read_text()
needle='    static constexpr double demand_weight = 1.0;'
assert needle in s;s=s.replace(needle,(p/'covariance.inc').read_text()+'\n'+needle)
a=s.index('    static double filler_gain(');b=s.index('\n    static constexpr double head_mix',a);fn=s[a:b]
fn=fn.replace('double p0 = 1, p1 = 0, expected = 0;', 'double p0 = 1, p1 = 0, expected = 0;\n        std::array<int,25>index{};std::array<double,25>good{},odds{};int count=0,zeros=0;double product=1,odds_sum=0;')
fn=fn.replace('            expected += p;', '''            expected += p;
            if(correlation_strength){index[count]=j;good[count]=1-p;if(good[count]>1e-12){product*=good[count];odds[count]=p/good[count];odds_sum+=odds[count];}else zeros++;count++;}''')
old='        return std::max(0.0, expected - (1 - p0) - 0.6 * (1 - p0 - p1));'
new='''        double value=expected-(1-p0)-.6*(1-p0-p1);
        if(correlation_strength){
            double correction=0;
            for(int a=0;a<count;a++)for(int b=a+1;b<count;b++){
                int remaining_zeros=zeros-(good[a]<=1e-12)-(good[b]<=1e-12);if(remaining_zeros>=2)continue;
                double z=product;if(good[a]>1e-12)z/=good[a];if(good[b]>1e-12)z/=good[b];
                double v0=remaining_zeros?0:z,v1=remaining_zeros?z:z*(odds_sum-odds[a]-odds[b]);
                int i=index[a],j=index[b];double covariance=head_covariance[i][j]*(((tb>>i)^(tb>>j))&1?-1:1);
                correction+=covariance*(.4*v0+.6*v1);
            }
            value+=correlation_strength*correction;value=std::min(value,std::max(0.,count-1.6));
        }
        return std::max(0.,value);'''
assert old in fn;fn=fn.replace(old,new);s=s[:a]+fn+s[b:]
s=s.replace('''    void filler_climb(double seconds, int fixedIterations = 0) {
        refresh_reset();''','''    void filler_climb(double seconds, int fixedIterations = 0) {
        refresh_reset();refresh_covariance();''')
(p/'main.cpp').write_text(s)
prob=(p.parent/'head-prob/prob.hpp').read_text().replace(' void update_probability(){',' void update_probability(){\n  d.refresh_covariance();')
(p/'prob.hpp').write_text(prob)
