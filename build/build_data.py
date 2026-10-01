"""Build the era-pooled school rows behind the UCSD local-schools predictor page.
Inputs (Svetlana folder):
  UCSD Lott Update 2026-08-12/ucsd_lott_panel_2015_2025.csv        UCSD counts + school context, 2015-2025
  UCSD Local Preference 2026-09-29/panel_ucsd_local_with_covariates.csv  other-campus counts, UC-wide pool, UCSD enrollees 1994+
  ucsd-local-preference/data/schools.csv                            district groups for San Diego / Imperial schools
Output: data/ucsd_local_data.json (embedded in index.html) + data/school_era_rows.csv"""
import pandas as pd, numpy as np, json, sys, os
ROOT=sys.argv[1] if len(sys.argv)>1 else '../..'
L=pd.read_csv(f'{ROOT}/UCSD Lott Update 2026-08-12/ucsd_lott_panel_2015_2025.csv',dtype={'ceeb':str,'cds14':str})
P=pd.read_csv(f'{ROOT}/UCSD Local Preference 2026-09-29/panel_ucsd_local_with_covariates.csv',dtype={'ceeb':str,'cds14':str})
S=pd.read_csv(f'{ROOT}/ucsd-local-preference/data/schools.csv',dtype={'ceeb':str,'cds14':str,'district':str})
ERAS={'base':(2015,2017,'2015–17'),'surge':(2018,2021,'2018–21'),'recent':(2022,2025,'2022–25')}
YIELD_WIN={'base':range(2010,2015),'surge':range(2013,2018),'recent':range(2017,2022)}
GROUPS=['Sweetwater Union High School District','San Diego Unified School District','Imperial County',
        'Poway, San Dieguito and Carlsbad districts','Other San Diego County schools','Rest of California']
grp=S.set_index('ceeb').dgroup.to_dict()
L=L.merge(P[['ceeb','year','oth_app','oth_adm','uw_app','uw_gpa','local']],on=['ceeb','year'],how='left')
L['grp']=L.ceeb.map(grp)
L.loc[L.grp.isna(),'grp']=np.where(L.loc[L.grp.isna(),'county'].isin(['San Diego','Imperial']),4,5)
L.loc[L.county.eq('Imperial')&L.grp.ne(2),'grp']=2
def wmean(x,w):
    m=x.notna()&w.notna()&(w>0); return np.nan if not m.any() else float((x[m]*w[m]).sum()/w[m].sum())
def ratio(a,b):
    m=a.notna()&b.notna()&(b>0); return np.nan if not m.any() else float(100*a[m].sum()/b[m].sum())
rows=[]
for era,(y0,y1,lab) in ERAS.items():
    E=L[L.year.between(y0,y1)]
    for ceeb,g in E.groupby('ceeb'):
        vis=g[g.admits.notna()]; A=vis.applicants.sum(); Atot=g.applicants.sum()
        if A<30 or A<0.5*Atot: continue
        last=g.iloc[-1]; ny=len(vis)
        y=P[(P.ceeb==ceeb)&P.year.isin(YIELD_WIN[era])]
        ym=y.sd_adm.notna()&y.sd_enr.notna(); dj=y.sd_adm[ym].sum(); ej=y.sd_enr[ym].sum(); dobs=y.sd_adm.sum()
        oy=100*ej/dj if (dj>=15 and dobs>0 and dj/dobs>=0.5) else np.nan
        upp=g.upp_pct.mean()
        r=dict(name=str(last.school_name).title().replace(' High School',' High')[:40],city=str(last.city)[:20],ceeb=ceeb,
          A=int(A),adm=100*vis.admits.sum()/A,K=int(vis.admits.sum()),grp=int(last.grp),
          ela=g.ela_pct_met.mean(),math=g.math_pct_met.mean(),agcomp=ratio(g.ag_met_uccsu_count,g.ag_cohort),
          upp=upp,sed=g.sed_pct.mean(),el=g.el_pct.mean(),lcffd=np.nan if pd.isna(upp) else float(upp>75),
          s_hisp=g.sch_hisp.mean(),s_white=g.sch_white.mean(),s_asian=g.sch_asian.mean(),s_black=g.sch_black.mean(),
          charter=g.charter.mean(),
          inc=g.tract_inc.mean()/1000,ba=g.tract_ba.mean(),pov=g.tract_pov.mean(),homeval=g.tract_homeval.mean()/1000,
          appgpa=wmean(g.app_gpa,g.applicants),gpa_gap=wmean(g.app_gpa,g.applicants)-wmean(g.uw_gpa,g.uw_app),
          apprate=ratio(g.applicants,g.ag_met_uccsu_count),ucsd_share=ratio(g.applicants,g.uw_app),
          logA=np.log10(Atot/len(g)),H=g.enroll_9_12.mean(),
          oth_rate=ratio(g.oth_adm,g.oth_app),
          o_grad6=g.o_grad6.mean(),o_yield=oy,
          dist=np.log10(max(g.dist_km_ucsd.mean(),1.0)) if g.dist_km_ucsd.notna().any() else np.nan,
          infl=g.infl_index.mean(),era=era)
        rows.append(r)
D=pd.DataFrame(rows)
D['local']=(D.grp<5).astype(float)
# where gpa_gap could not be computed (no UC-wide pool row) leave blank
VARS=['ela','math','agcomp','upp','sed','el','lcffd','s_hisp','s_white','s_asian','s_black','charter',
      'inc','ba','pov','homeval','appgpa','gpa_gap','apprate','ucsd_share','logA','H','oth_rate','o_grad6','o_yield','infl',
      'local','dist']
DEC={'appgpa':3,'gpa_gap':3,'logA':3,'dist':3,'infl':3,'lcffd':0,'local':0,'charter':0,'H':0,'homeval':0}
COLS=['name','city','ceeb','A','adm','K','grp']+VARS
cells={}
for era in ERAS:
    d=D[D.era==era]; out=[]
    for _,x in d.iterrows():
        row=[x['name'],x.city,x.ceeb,int(x.A),round(float(x.adm),2),int(x.K),int(x.grp)]
        for v in VARS:
            val=x[v]; row.append(None if pd.isna(val) else round(float(val),DEC.get(v,1)))
        out.append(row)
    cells[era]=out
DATA={'cols':COLS,'vars':VARS,'cells':cells,'eras':{k:v[2] for k,v in ERAS.items()},'groups':GROUPS}
os.makedirs('../data',exist_ok=True)
json.dump(DATA,open('../data/ucsd_local_data.json','w'),separators=(',',':'),ensure_ascii=False)
D.to_csv('../data/school_era_rows.csv',index=False)
print(D.groupby(['era','grp']).agg(n=('ceeb','size'),A=('A','sum'),K=('K','sum')).assign(rate=lambda t:100*t.K/t.A).round(1))
print(D.groupby('era')[VARS].apply(lambda t:t.notna().mean().round(2)).T)
