#!/usr/bin/env Rscript
# Figure contract: compare priority-list stability under individual weight and model-structure perturbations.
# Quantitative grid adapted in style only from the supplied figure; new data and explicit metrics.
# width_mm = 183; height_mm = 88. R only; Arial >=7 pt; editable text; 600 dpi PNG.
suppressPackageStartupMessages({library(ggplot2);library(patchwork)})
root<-'/Users/ruiwang/Projects/APPs/PlastPrior'
args<-commandArgs(trailingOnly=TRUE);stopifnot(length(args)==1L)
stage<-normalizePath(args[1]);fd<-stage
z<-readRDS(file.path(stage,'source_data/plot_data.rds'))
p<-z$points;h<-z$heat
rank<-aggregate(jaccard_pct~display,p,min);rank<-rank[order(rank$jaccard_pct,rank$display),]
p$display<-factor(p$display,levels=rev(rank$display));p$y<-as.numeric(p$display)
p$cohort<-factor(p$cohort,levels=c('Level 1','Levels 1 + 2'))
p$yp<-p$y+ifelse(p$cohort=='Level 1',.11,-.11)
rowlines<-data.frame(y=1:10)
font<-'Arial';ink<-'#263746'
theme_set(theme_classic(base_size=8,base_family=font)+
 theme(axis.text=element_text(size=7,colour=ink),axis.title=element_text(size=7.5),
 axis.line=element_line(linewidth=.3,colour='#677783'),axis.ticks=element_line(linewidth=.3),
 plot.title=element_text(size=10,face='bold',colour=ink),
 plot.subtitle=element_text(size=7.5,lineheight=1.15,colour='#5E6B76'),
 plot.title.position='plot',plot.margin=margin(6,6,6,5),
 plot.tag=element_text(size=11,face='bold',colour=ink),
 legend.text=element_text(size=7),legend.title=element_text(size=7),legend.position='top',
 legend.margin=margin(0,0,3,0),legend.key.width=grid::unit(8,'mm')))
pa<-ggplot(p,aes(jaccard_pct,yp,colour=cohort,shape=cohort))+
 geom_segment(data=rowlines,aes(x=40,xend=100,y=y,yend=y),inherit.aes=FALSE,colour='#E8EDF0',linewidth=.35)+
 geom_vline(xintercept=100,colour='#A9B5BE',linetype='dashed',linewidth=.35)+
 geom_point(size=2.55,stroke=.3)+
 scale_colour_manual(values=c('Level 1'='#B9413B','Levels 1 + 2'='#2E788A'),name=NULL)+
 scale_shape_manual(values=c('Level 1'=16,'Levels 1 + 2'=18),name=NULL)+
 scale_x_continuous(limits=c(40,102),breaks=c(40,60,80,100),labels=c('40','60','80','100'),expand=c(0,0))+
 scale_y_continuous(breaks=1:10,labels=levels(p$display),limits=c(.5,10.5),expand=c(0,0))+
 labs(x='Jaccard similarity (%)',y=NULL,tag='a')+
 theme(axis.line.y=element_blank(),axis.ticks.y=element_blank())+
 guides(colour=guide_legend(nrow=1),shape=guide_legend(nrow=1))
h$scenario<-gsub('Equal P/B/M/T weights','Equal PBMT weights',h$scenario,fixed=TRUE)
h$scenario<-gsub('Inventory weight halved','Inventory weight × 0.5',h$scenario,fixed=TRUE)
h$scenario<-gsub('vH cutoff: 12 → ','vH ≥ ',h$scenario,fixed=TRUE)
scenario_order<-unique(h$scenario)
h$scenario<-factor(h$scenario,levels=rev(scenario_order))
h$metric<-factor(h$metric,levels=c('All levels','Level 1','Levels 1 + 2'))
h$label<-sprintf('%.1f',h$value_pct)
pb<-ggplot(h,aes(metric,scenario,fill=value_pct))+
 geom_tile(colour='white',linewidth=.7)+
 geom_text(aes(label=label,colour=value_pct>=68),size=2.65,family=font)+
 scale_colour_manual(values=c('TRUE'='white','FALSE'=ink),guide='none')+
 scale_fill_gradient(low='#F1F4F6',high='#29465D',limits=c(0,100),breaks=c(0,50,100),labels=c('0%','50%','100%'),name=NULL)+
 scale_x_discrete(labels=c('All levels'='Level\nagreement','Level 1'='Level 1\nJaccard','Levels 1 + 2'='Level 1 + 2\nJaccard'),expand=c(0,0))+
 scale_y_discrete(expand=c(0,0))+
 labs(x=NULL,y=NULL,tag='b')+
 guides(fill=guide_colourbar(direction='vertical',barwidth=grid::unit(2.5,'mm'),barheight=grid::unit(22,'mm'),
 title.position='top',title.hjust=0))+
 theme(axis.line=element_blank(),axis.ticks=element_blank(),legend.position='right',
 axis.text.x=element_text(size=7,lineheight=1.1),axis.text.y=element_text(size=7),
 legend.title=element_text(size=7),legend.text=element_text(size=7))
fig<-(pa|pb)+plot_layout(widths=c(1,1.22))+
 plot_annotation(theme=theme(plot.margin=margin(5,5,5,5)))
source(file.path(root,'FigureCode/_shared/export.R'))
# Editable vectors via svglite::svglite() and grDevices::cairo_pdf(); 600 dpi ragg::agg_png().
export_figure(fig,file.path(fd,'Fig5'),183,88,dpi=600,
 formats=c('svg','pdf','png'),font_family=font)
# Verify editable text with svglite; the current public result set retains PNG/PDF only.
svg<-file.path(fd,'Fig5.svg')
stopifnot(any(grepl('<text',readLines(svg,warn=FALSE),fixed=TRUE)))
unlink(svg)
