#!/usr/bin/env Rscript
# Prepare sensitivity scenarios only; never overwrite official scores or ranking.
source('FigureCode/_shared/managed.R')
input<-file.path(repo_root,lock$files$publication$path)
stopifnot(sha256_file(input)==lock$files$publication$sha256)
x<-as.data.frame(readr::read_csv(input,show_col_types=FALSE))
p<-jsonlite::fromJSON(file.path(repo_root,'plastprior/scenario_policy.json'))
f<-jsonlite::fromJSON(file.path(repo_root,lock$policy$path))
w<-unlist(c(p$hazard_weights,p$exposure_weights));cols<-names(w)
labels<-c('Persistence','Mobility','Bioaccumulation','Toxicity','Food contact',
 'Biomonitoring','Inventory','Production','Patents','Literature')
q<-as.matrix(x[,cols]);q[is.na(q)]<-0;q<-q*4
mx<-ifelse(cols %in% c('Exposure_food_contact_score','Exposure_human_biomonitoring_score'),1,2)
stopifnot(nrow(x)==15125L,!anyDuplicated(x$inchikey),all(q==round(q)))
classify<-function(h,e,hcuts=c(4,8,12),ecuts=c(4,8,12))
 f$level_matrix_L_M_H_vH[cbind(findInterval(h,hcuts)+1L,findInterval(e,ecuts)+1L)]
compute<-function(weights=w,hcuts=c(4,8,12),ecuts=c(4,8,12)) {
 iw<-round(weights*10);stopifnot(all(abs(iw-weights*10)<1e-8))
 calc<-function(ii) {
  num<-as.vector(q[,ii,drop=FALSE]%*%iw[ii])*16;den<-4*sum(iw[ii]*mx[ii])
  (2*num+den)%/%(2*den)
 }
 h<-calc(1:4);e<-calc(5:10)
 list(h=h,e=e,lev=classify(h,e,hcuts,ecuts))
}
b<-compute();base<-classify(x$Hazard_score,x$Exposure_score)
stopifnot(all(b$h==x$Hazard_score),all(b$e==x$Exposure_score),all(b$lev==base),
 all(tabulate(base,5)==f$expected_counts))
points<-list();k<-0L
for(j in seq_along(cols))for(delta in c(-20,20)) {
 weights<-w;weights[j]<-weights[j]*(100+delta)/100;lev<-compute(weights)$lev
 for(lim in c(1,2)) {
  before<-base<=lim;after<-lev<=lim;k<-k+1L
  points[[k]]<-data.frame(component=cols[j],display=labels[j],change_pct=delta,
   cohort=if(lim==1)'Level 1' else 'Levels 1 + 2',intersection_n=sum(before&after),
   union_n=sum(before|after),baseline_n=sum(before),jaccard_pct=100*sum(before&after)/sum(before|after))
 }
}
points<-do.call(rbind,points)
plot_points<-do.call(rbind,lapply(split(points,list(points$component,points$cohort),drop=TRUE),function(v)v[which.min(v$jaccard_pct),]))
save_table(points,'weight_scenarios');save_table(plot_points,'weight_points')
specs<-list(
 list(id='baseline',label='Baseline',weights=w,hcuts=c(4,8,12),ecuts=c(4,8,12)),
 list(id='equal_hazard',label='Equal P/B/M/T weights',weights=replace(w,1:4,1),hcuts=c(4,8,12),ecuts=c(4,8,12)),
 list(id='equal_exposure',label='Equal exposure weights',weights=replace(w,5:10,1),hcuts=c(4,8,12),ecuts=c(4,8,12)),
 list(id='half_inventory',label='Inventory weight halved',weights=replace(w,which(cols=='Exposure_inventory_score'),1.5),hcuts=c(4,8,12),ecuts=c(4,8,12)),
 list(id='hazard_vh11',label='Hazard vH cutoff: 12 → 11',weights=w,hcuts=c(4,8,11),ecuts=c(4,8,12)),
 list(id='hazard_vh13',label='Hazard vH cutoff: 12 → 13',weights=w,hcuts=c(4,8,13),ecuts=c(4,8,12)),
 list(id='exposure_vh11',label='Exposure vH cutoff: 12 → 11',weights=w,hcuts=c(4,8,12),ecuts=c(4,8,11)),
 list(id='exposure_vh13',label='Exposure vH cutoff: 12 → 13',weights=w,hcuts=c(4,8,12),ecuts=c(4,8,13)))
heat<-list();trans<-list();settings<-list()
for(i in seq_along(specs)) {
 s<-specs[[i]];v<-compute(s$weights,s$hcuts,s$ecuts);lev<-v$lev
 vals<-c(100*mean(lev==base),sapply(c(1,2),function(lim)100*sum(base<=lim & lev<=lim)/sum(base<=lim | lev<=lim)))
 heat[[i]]<-data.frame(id=s$id,scenario=s$label,metric=c('All levels','Level 1','Levels 1 + 2'),value_pct=vals)
 tr<-as.data.frame(table(baseline_level=factor(base,levels=1:5),scenario_level=factor(lev,levels=1:5)))
 names(tr)[3]<-'n';tr$id<-s$id;trans[[i]]<-tr
 settings[[i]]<-data.frame(id=s$id,scenario=s$label,component=cols,weight=as.numeric(s$weights),
 hazard_cuts=paste(s$hcuts,collapse=';'),exposure_cuts=paste(s$ecuts,collapse=';'),normalization='each domain maximum 16')
 stopifnot(sum(tr$n)==15125L)
}
heat<-do.call(rbind,heat);trans<-do.call(rbind,trans);settings<-do.call(rbind,settings)
stopifnot(nrow(points)==40L,nrow(plot_points)==20L,nrow(heat)==24L,
 all(heat$value_pct[heat$id=='baseline']==100),all(heat$value_pct>=0 & heat$value_pct<=100))
save_table(heat,'model_scenarios');save_table(trans,'model_transitions');save_table(settings,'model_settings')
save_plot_data(list(points=plot_points,heat=heat))
save_facts(list(population=nrow(x),baseline_level_counts=as.integer(tabulate(base,5)),
 weight_perturbations_pct=c(-20,20),point_definition='Lower Jaccard similarity across the two perturbation directions, independently for each cohort.',
 row_order='Ascending minimum Jaccard across the two cohorts; alphabetical ties.',
 list_metric='Intersection divided by union, percent.',agreement_metric='Percent of all compounds retaining the same five-level classification.',
 domain_maximum=16,rounding='Exact rational half-up after domain sum',baseline_cutpoints=c(4,8,12),
 missingness='Missing component contributes zero to sum only; raw evidence unchanged.',scenario_count=8,
 scope='Sensitivity scenarios only. Official scores, ranks and Top-N membership unchanged.'))
