+++
abstract = "In multi-party democracies, election coverage usually focuses on raw results from polls on questions like 'Who would you vote for if the election was tomorrow?' Whether a coalition (union of multiple parties) will obtain enough votes to form a governing coalition is discussed by adding up votes obtained by the parties in question, while ignoring sample uncertainty and redistribution of votes for parties beneath a specific threshold (e.g., 5% in Germany). The [**R**](https://www.r-project.org/) package [`coalitions`](https://adibender.github.io/coalitions/) implements methods that overcome those shortcomings and quantifies sample uncertainty in terms of probabilities for events of interest. Specifically, it contains functions to (a) Obtain survey results from different polling agencies, (b) Aggregate (pool) multiple surveys (from different pollsters) within a pre-specified time-window, taking into account the correlation between different polling agencies, perform Monte Carlo simulations of election outcomes based on the (pooled) survey results, redistribute votes based on the method specific to the election of interest (e.g., Saint-Lague-Scheppers for German *Bundestag* election), calculate Bayesian posterior probabilities for specific events, e.g., to obtain enough votes (> 50%) to form a governing coalition. To get started, the [workflow vignette ](https://adibender.github.io/coalitions/articles/workflow.html) describes the usual steps during the analysis; the [pooling vignette](https://adibender.github.io/coalitions/articles/pooling.html) gives details on the aggregation of multiple surveys. An example for the (backend) application of the package can be found at [http://koala.stat.uni-muenchen.de](http://koala.stat.uni-muenchen.de), where it is applied to German (federal and state wide) elections/surveys."
authors = ["A Bender", "A Bauer"]
date = "2018-03-11"
image_preview = "shares_animated.gif"
publication_types = ["7"]
publication = "In *Journal of Open Source Software*."
title = "coalitions: Coalition probabilities in multi-party democracies"
selected = false
url_pdf = "https://www.theoj.org/joss-papers/joss.00606/10.21105.joss.00606.pdf"
[[url_custom]]
name = "DOI: doi.org/10.21105/joss.00606"
url = "http://joss.theoj.org/papers/10.21105/joss.00606"




# Optional featured image (relative to `static/img/` folder).
[header]
image = ""
caption = ""
+++
