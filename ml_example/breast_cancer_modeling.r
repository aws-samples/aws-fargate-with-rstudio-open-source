install.packages(c('caret', 'mlbench', 'gbm', 'e1071', 'tidyverse'))
library(caret)
library(mlbench)

data(BreastCancer)
summary(BreastCancer) #Summary of Dataset

df <- BreastCancer
# convert input values to numeric
for(i in 2:10) {
  df[,i] <- as.numeric(as.character(df[,i]))
}

# split the data into train and test and perform preprocessing
trainIndex <- createDataPartition(df$Class, p = .8, 
                                  list = FALSE, 
                                  times = 1)
df_train <- df[ trainIndex,]
df_test  <- df[-trainIndex,]
preProcValues <- preProcess(df_train, method = c("center", "scale", "medianImpute"))
df_train_transformed <- predict(preProcValues, df_train)
df_test_transformed <- predict(preProcValues, df_test)

# train a model on df_train
fitControl <- trainControl(## 10-fold CV
                          method = "repeatedcv",
                          number = 10,
                          ## repeated ten times
                          repeats = 10,
                          ## Estimate class probabilities
                          classProbs = TRUE,
                          ## Evaluate performance using 
                          ## the following function
                          summaryFunction = twoClassSummary)

set.seed(825)
gbmFit1 <- train(Class ~ ., data = df_train_transformed[,2:11], 
                 method = "gbm", 
                 trControl = fitControl,
                 ## This last option is actually one
                 ## for gbm() that passes through
                 verbose = FALSE,
                 metric = "ROC")
gbmFit1

predict(gbmFit1, newdata = df_test_transformed[,2:11], type = "prob")

saveRDS(preProcValues, file = './breast-cancer-prediction/preProcessor.rds')
saveRDS(gbmFit1, file = './breast-cancer-prediction/gbm_model.rds')
saveRDS(df_test, file = './breast-cancer-prediction/breast_cancer_test_data.rds')


