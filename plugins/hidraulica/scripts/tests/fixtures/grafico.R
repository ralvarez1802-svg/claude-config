library(ggplot2)
p <- ggplot(datos, aes(x = t, y = q)) + geom_line()
ggsave("hidrograma.pdf", p)
