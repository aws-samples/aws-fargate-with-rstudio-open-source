install.packages(c('caret', 'mlbench', 'tidyverse'))
library(caret)
library(mlbench)

data(BreastCancer)
summary(BreastCancer) #Summary of Dataset

df <- BreastCancer
# convert input values to numeric
for(i in 2:10) {
  df[,i] <- as.numeric(as.character(df[,i]))
}


trainIndex <- createDataPartition(df$Class, p = .8, 
                                  list = FALSE, 
                                  times = 1)
df_train <- df[ trainIndex,]
df_test  <- df[-trainIndex,]
preProcValues <- preProcess(df_train, method = c("center", "scale", "medianImpute"))
df_train_transformed <- predict(preProcValues, df_train)
df_test_transformed <- predict(preProcValues, df_test)
