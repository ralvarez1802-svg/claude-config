datos <- read.csv("crudo.csv")
datos <- datos[!is.na(datos$pp), ]
write.csv(datos, "limpio.csv", row.names = FALSE)
