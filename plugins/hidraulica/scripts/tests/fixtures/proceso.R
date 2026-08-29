library(openxlsx)
datos <- read.csv("estaciones.csv")
resumen <- aggregate(pp ~ anio, datos, sum)
write.xlsx(resumen, "balance_hidrico.xlsx")
