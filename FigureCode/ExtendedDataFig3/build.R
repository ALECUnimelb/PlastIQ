#!/usr/bin/env Rscript
# Quantitative grid: GIC context, fixed-budget capture and its weight dependence.
# R-only rendering; width_mm = 183; height_mm = 145; Arial >=6.5 pt; 600 dpi.
suppressPackageStartupMessages({library(ggplot2);library(patchwork)})
script <- normalizePath(sub('^--file=','',grep('^--file=',commandArgs(FALSE),value=TRUE)[1]))
root <- dirname(dirname(dirname(script)))
args <- commandArgs(trailingOnly=TRUE);stopifnot(length(args)==1L)
stage <- normalizePath(args[1])
z <- readRDS(file.path(stage,'source_data/plot_data.rds'))
comp <- z$composition;b <- z$comparison;w <- z$weights
codes <- c('prohibited_or_phaseout','restricted_or_authorisation_required','candidate_or_high_concern',
 'monitoring_reporting_or_hazard_classification','inventory_registration_or_use_only','not_listed')
labels <- c('Prohibited / phase-out','Restricted / authorisation','Candidate / high concern',
 'Monitoring / reporting / hazard','Inventory / registration / use','No matched GIC record')
palette <- setNames(c('#79352F','#B66E61','#CEA65F','#528995','#A9BCC6','#E6E9EC'),codes)
font <- 'Arial';ink <- '#263746'
theme_set(theme_classic(base_size=8,base_family=font)+
 theme(axis.text=element_text(size=7,colour=ink),axis.title=element_text(size=7.5),
 plot.title=element_text(size=8.5,face='bold'),plot.subtitle=element_text(size=7,colour='#53606D'),
 plot.tag=element_text(size=10,face='bold'),plot.margin=margin(5,6,5,5),
 legend.text=element_text(size=6.5),legend.key.height=grid::unit(3,'mm'),
 legend.key.width=grid::unit(4,'mm'),legend.margin=margin(0,0,0,0)))
comp$status <- factor(comp$status,levels=codes)
ns <- tapply(comp$n,comp$level,sum)
comp$level_label <- factor(paste0('Level ',comp$level,' (',format(ns[as.character(comp$level)],big.mark=',',trim=TRUE),')'),
 levels=rev(paste0('Level ',1:5,' (',format(ns,big.mark=',',trim=TRUE),')')))
pa <- ggplot(comp,aes(pct,level_label,fill=status))+
 geom_col(width=.68,position=position_stack(reverse=TRUE))+
 scale_fill_manual(values=palette,breaks=codes,labels=labels,drop=FALSE)+
 scale_x_continuous(breaks=c(0,25,50,75,100),expand=expansion(mult=c(0,.01)))+
 coord_cartesian(xlim=c(0,100))+
 labs(x='Compounds within each level (%)',y=NULL,fill=NULL,tag='a')+
 guides(fill=guide_legend(ncol=1,byrow=TRUE))+
 theme(legend.position='bottom',legend.justification='left',axis.ticks.y=element_blank(),
       legend.box.spacing=grid::unit(1,'mm'))
b$row <- 4:1;b$label <- sprintf('%.2f%%',b$capture_pct)
baseline <- b$capture_pct[b$scenario=='baseline']
method_palette <- c(baseline='#A9463E',hazard_only='#36495D',exposure_only='#337C8B',no_inventory='#C88736')
pb <- ggplot(b,aes(capture_pct,row))+
 geom_segment(aes(x=0,xend=capture_pct,yend=row),colour='#D5DDE3',linewidth=.8)+
 geom_vline(xintercept=baseline,linetype=2,colour='#9AA7B2',linewidth=.4)+
 geom_point(aes(colour=scenario),size=2.5)+
 geom_text(aes(x=20.6,label=label),hjust=0,size=2.55,colour=ink)+
 scale_colour_manual(values=method_palette,guide='none')+
 scale_x_continuous(limits=c(0,26),breaks=c(0,5,10,15,20),expand=expansion(mult=0))+
 scale_y_continuous(breaks=4:1,labels=c('Integrated','Hazard only','Exposure only','No inventory'),
                    limits=c(.5,4.5),expand=expansion(mult=0))+
 labs(x='Captured (% of 1,451)',y=NULL,tag='b',title='Top 5% screened',subtitle=sprintf('Baseline: %.2f%%',baseline))+
 theme(axis.line.y=element_blank(),axis.ticks.y=element_blank())
order <- unlist(z$config$components);cn <- unlist(z$config$component_labels)
w$row <- match(w$component,rev(order));w$column <- ifelse(w$multiplier<1,1,2)
delta <- ifelse(abs(w$delta_capture_pp)<.01 & w$delta_capture_pp!=0,
 sprintf('%+.3f',w$delta_capture_pp),sprintf('%+.2f',w$delta_capture_pp))
w$label <- sprintf('%.2f (%s)',w$capture_pct,delta)
pc <- ggplot(w,aes(column,row))+
 geom_tile(aes(fill=delta_capture_pp),width=.97,height=.91,colour='white',linewidth=.3)+
 geom_text(aes(label=label),size=2.65,colour=ink)+
 scale_fill_gradient2(low='#D9E7EF',mid='white',high='#F0D8CF',midpoint=0,limits=c(-1,1)*max(.5,abs(w$delta_capture_pp)),guide='none')+
 scale_y_continuous(limits=c(.5,10.5),breaks=1:10,labels=unname(cn[rev(order)]),expand=expansion(mult=0))+
 scale_x_continuous(limits=c(.5,2.5),breaks=1:2,labels=c('Weight -20%','Weight +20%'),position='top',expand=expansion(mult=0))+
 labs(x=NULL,y=NULL,tag='c',title='Capture % (change in percentage points)',subtitle=sprintf('Top 5%% screened; baseline: %.2f%%',baseline))+
 theme(axis.line=element_blank(),axis.ticks=element_blank(),
       axis.text.x=element_text(size=7.5,face='bold',margin=margin(b=4)))
figure <- ((pa|pb)/pc)+plot_layout(heights=c(1,1.02),widths=c(1.1,1))+
 plot_annotation(theme=theme(plot.margin=margin(4,4,4,4)))
source(file.path(root,'FigureCode/_shared/export.R'))
# Helper uses svglite::svglite(), grDevices::cairo_pdf(), and ragg::agg_png() at 600 dpi.
export_figure(figure,file.path(stage,'ExtendedDataFig3'),183,145,dpi=600,
 formats=c('svg','pdf','png'),font_family=font)
svg <- file.path(stage,'ExtendedDataFig3.svg')
stopifnot(any(grepl('<text',readLines(svg,warn=FALSE),fixed=TRUE)))
unlink(svg)
