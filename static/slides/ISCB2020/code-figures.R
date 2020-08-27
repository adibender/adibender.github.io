## load needed libraries
library(ggplot2)
theme_set(theme_bw())
library(magrittr)
library(tidyr)
library(purrr)
library(dplyr)
library(survival)
library(mgcv)
library(pammtools)
library(grid)
library(gridExtra)

## color pallets
Set1    <- RColorBrewer::brewer.pal(9, "Set1")
Greens  <- RColorBrewer::brewer.pal(9, "Greens")
Purples <- RColorBrewer::brewer.pal(9, "Purples")


#### Motivational figure
hweibull <- function(t, alpha=1.5, tau=2) {
  (alpha/tau) * (t/tau)^(alpha -1)
}

tdf <- data.frame(time = seq(0, 3, by=0.01)) %>%
  mutate(hweib = hweibull(time))

set.seed(16042017)
sdata <- data.frame(time=rweibull(500, 1.5, 2)) %>%
  mutate(event=1)

gg.base <- ggplot(tdf, aes(x=time, y=hweib)) +
  geom_line() +
  ylab(expression(lambda(t))) +
  xlab("t")



kappa5 <- c(0, 1, 1.5, 3)
ped5 <- split_data(Surv(time, event)~., data=sdata, cut=kappa5, id="id")
pam5 <- gam(ped_status ~ interval, data=ped5, family=poisson(), offset=offset)
pred5 <- ped5 %>% int_info() %>% add_hazard(pam5)


p_base <- gg.base
p_cuts <- gg.base + geom_vline(xintercept = kappa5, lty=2) +
          scale_x_continuous(
                breaks = kappa5,
            labels=c(
              expression(kappa[0]==0),
              expression(kappa[1]==1),
              expression(kappa[2]==1.5),
              expression(kappa[3]==3)))
p_est <- p_cuts + geom_stephazard(data=pred5, aes(x=tend, y=hazard))

ggsave("p-base.png", p_base,  width = 5, height = 5)
ggsave("p-cuts.png", p_cuts, width = 5, height = 5)
ggsave("p-est.png", p_est, width = 5, height = 5)


pdf("weibullHazard.pdf", width=9, height=3)
grid.draw(
    cbind(
        ggplotGrob(gg.base),
        ggplotGrob(gg.base +  geom_vline(xintercept = kappa5, lty=2) +
          scale_x_continuous(
                breaks = kappa5,
            labels=c(
              expression(kappa[0]==0),
              expression(kappa[1]==1),
              expression(kappa[2]==1.5),
              expression(kappa[3]==3)))),
        ggplotGrob(gg.base + geom_vline(xintercept = c(1, 1.5, 3), lty=2) +
          geom_stephazard(data=pred5, aes(x=tend, y=hazard)) +
          scale_x_continuous(
                breaks = c(0, 1, 1.5, 3),
            labels=c(
              expression(kappa[0]==0),
              expression(kappa[1]==1),
              expression(kappa[2]==1.5),
              expression(kappa[3]==3)))),
        size = "last"))
dev.off()
