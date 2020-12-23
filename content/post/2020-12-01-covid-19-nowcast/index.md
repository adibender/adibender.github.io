---
aliases: [nowcast-publication]
projects: []
title: 'New paper: "Nowcasting the COVID-19 Pandemic in Bavaria"'
authors: [adibender]
date: '2020-12-01'
tags: [papers, nowcasting, Bayes, COVID-19]
categories:
  - papers,
  - nowcasting
summary: "Nowcasting the COVID-19 Pandemic in Bavaria"
image:
  caption: ''
  focal_point: ''
output:
  blogdown::html_page:
    toc: true
    number_sections: true
    toc_depth: 1
---

Our paper, ["Nowcasting the COVID-19 Pandemic in Bavaria"](https://onlinelibrary.wiley.com/doi/full/10.1002/bimj.202000112), has been published in the Biometrical Journal. Code and anonymzed data are openly available and have been checked by the reproducibility editors of the Journal. Updated analyses are available via shiny app: https://corona.stat.uni-muenchen.de/nowcast/.
The abstract is given below:

"To assess the current dynamics of an epidemic, it is central to collect informa-
tion on the daily number of newly diseased cases. This is especially important in
real-time surveillance, where the aim is to gain situational awareness, for exam-
ple, if cases are currently increasing or decreasing. Reporting delays between
disease onset and case reporting hamper our ability to understand the dynam-
ics of an epidemic close to now when looking at the number of daily reported
Nowcasting can be used to adjust daily case counts for occurred-but-
not-yet-reported events. Here, we present a novel application of nowcasting to
data on the current COVID-19 pandemic in Bavaria. It is based on a hierarchical
Bayesian model that considers changes in the reporting delay distribution over
time and associated with the weekday of reporting. Furthermore, we present a
way to estimate the effective time-varying case reproduction number R e (t) based
on predictions of the nowcast. The approaches are based on previously published
work, that we considerably extended and adapted to the current task of now-
casting COVID-19 cases. We provide methodological details of the developed
approach, illustrate results based on data of the current pandemic, and evalu-
ate the model based on synthetic and retrospective data on COVID-19 in Bavaria.
Results of our nowcasting are reported to the Bavarian health authority and pub-
lished on a webpage on a daily basis (https://corona.stat.uni-muenchen.de/).
Code and synthetic data for the analysis are available from https://github.com/
FelixGuenther/nc_covid19_bavaria and can be used for adaption of our approach
to different data."
