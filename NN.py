import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler # OneHotEncoder, QuantileTransformer,
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import r2_score,mean_squared_error,mean_absolute_error
# from time import time
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.inspection import permutation_importance
import os
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
import matplotlib.pyplot as plt

from dataclasses import dataclass, field

@dataclass(kw_only=True)
class defaultSettings:
    nModels: int = 3
    activation: str = 'relu'
    hiddenLayerShape: tuple = (64)
    seed: int = 42
    test_split: float = 0.1
    validate_split: float = 0.1
    scaleY: bool = True

class ensembleNN(defaultSettings):
    # Train an ensemble of (single layer default) Dense Feed Forward Neural Networks
    # Scales data (without using pipeline mode) for increased flexibility and transparency
    # Trains NN (early stopping using validation set)
    # Evaluates model to get the test score (mean & 95% CI from ensemble)
    # From ensemble, calculates mean prediction and 95%CI from variance of estimates
    # Calculates partial derivatives (using test data) to:
    #   1. Evaluate feature importance with Sum of Squared Derivatives (and sign)
    #   2. Map response functions over feature space
    #   3. Get confidence in response from ensemble mean and CI
    
    
    def trainEnsemble(self,dataTable,X,y):
        ix = (~dataTable[X+[y]].isna()).all(axis=1) 
        self.Ensemble = {}
        for nth in range(self.nModels):
            self.nthModel = {}
            self.seed += nth
            dataTable[f"{y}_ANN_f_{nth}"] = np.nan
            dataTable.loc[ix,f"{y}_ANN_f_{nth}"] = self.trainModel(dataTable.loc[ix,X+[y]],X,y)
            self.Ensemble[nth] = self.nthModel
        self.evaluateEnsemble(dataTable.loc[ix,X+[y]],X,y)

    def evaluateEnsemble(self,dataTable,X,y):
        for nth in range(self.nModels):
            dataTable[X] = self.Ensemble[nth]['X_scaler'].transform(dataTable[X])
            dataTable[y] = self.Ensemble[nth]['y_scaler'].transform(dataTable[[y]])
            self.calculateDerivatives(nth,dataTable,X,y)

    def trainModel(self,dataTable,X,y):
        # Split and scale the data for each model
        train,test = self.test_train_split(dataTable,X,y,scale=True)
        model = MLPRegressor(
                hidden_layer_sizes=(self.hiddenLayerShape),
                learning_rate='adaptive',
                early_stopping=True,
                solver='lbfgs',
                activation=self.activation,
                verbose=True,
                n_iter_no_change=2,
                random_state=self.seed,
                validation_fraction=self.validate_split,
                max_iter=500
            )
        model.fit(train[X],train[y])
        test_prediction = model.predict(test[X])
        self.nthModel['R2'] = r2_score(test[y],test_prediction)
        self.nthModel['RMSE'] = mean_squared_error(test[y],test_prediction)**.5
        self.nthModel['MAE'] = mean_absolute_error(test[y],test_prediction)
        self.nthModel['MLPRegressor'] = model
        return(model.predict(dataTable[X]))

    def test_train_split(self,dataTable,X,y,scale):
        # Split out the test set
        np.random.seed(self.seed)
        test_size = int(dataTable.shape[0]*self.test_split)
        test_set = np.random.randint(0, dataTable.shape[0],test_size)
        test_set = dataTable.iloc[test_set,:].copy()
        train_set = dataTable.loc[~dataTable.index.isin(test_set.index),:].copy()
        if scale == True:
            train_set,test_set = self.scaleVariables(train_set,test_set,X,y)
            return (train_set,test_set)    
        else:
            return (train_set,test_set)
        
    def scaleVariables(self,train,test,X,y):
        # Scale train[X], test[X] and train[y], test[y] by only the training set
        # For now just numeric, can add categorical later
        Xs,ys = StandardScaler(),StandardScaler()
        Xs.fit(train[X])
        ys.fit(train[[y]])
        self.nthModel['X_scaler'] = Xs
        self.nthModel['y_scaler'] = ys
        train[X] = Xs.transform(train[X])
        test[X] = Xs.transform(test[X])
        train[y] = ys.transform(train[[y]])
        test[y] = ys.transform(test[[y]])
        return(train,test)

    def calculateDerivatives(self,nth,featureSpace,X,y):
        # Get the model derivatives over the feature space for the nth model in the ensemble
        model = self.Ensemble[nth]['MLPRegressor']
        X_values = featureSpace[X].values
        target = featureSpace[y].values
        intercepts = model.intercepts_
        weights = model.coefs_
        Zeros = np.zeros(intercepts[0].shape)
        Ones = np.ones(intercepts[0].shape)
        # Do a "prediction pass" over the feature space
        # Could replace this with model.predict() instead for performance
        # For now calculating manually to ensure the math is transparent
        #   1) Ensure the same answer as the model predict
        #   2) Gives template for derivative calculations
        Prediction = []
        for i in range(X_values.shape[0]):
            Input = X_values[i]
            # breakpoint()
            H1 = ((Input*weights[0].T).sum(axis=1)+intercepts[0])
            if model.activation == 'relu':
                H1 = np.maximum(Zeros,H1)
            elif model.activation == 'logistic':
                H1 = 1/(1+np.exp(-H1))
            elif model.activation == 'tanh':
                H1 = np.tanh(H1)
            else:
                exit('Invalid activation')
            H2 = (H1*weights[1].T).sum()+intercepts[1]
            Prediction.append(H2)
        Prediction = np.array(Prediction)
        # Do a second pass on a per-feature basis to get partial derivatives

        Derivatives = []
        Sum_Derivatives = []
        Sum_Squared_Derivatives = []

        for i in range(X_values.shape[1]):
            dj = []
            # Loop over inputs per feature
            for j in range (X_values.shape[0]):
                Xj = X_values[j,i]
                H1 = Xj*weights[0][i,:]+intercepts[0]
                # Calculate the first derivative of the activation function for the per-variable Hidden Layer input
                if model.activation == 'relu':
                    H1 = np.maximum(Zeros,H1)
                    dH1 = H1.copy()
                    dH1[dH1>0] = 1
                elif model.activation == 'logistic':
                    H1 = 1/(1+np.exp(-H1))
                    dH1 = H1*(1-H1)
                elif model.activation == 'tanh':
                    H1 = np.tanh(H1)
                    dH1 = 1-np.square(H1)
                else:
                    exit('Invalid activation')
                # Derivative of output (a linear function)
                Sj = 1
                Sigma = np.array([weights[1][h]*dH1[h]*weights[0][i,h] for h in range(weights[1].shape[0])]).sum()
                dj.append(Sj*Sigma)
            dji = np.array(dj)
            Derivatives.append(dj)
            Sum_Derivatives.append(np.sum(dji))
            Sum_Squared_Derivatives.append(np.sum(dji**2))

        Derivatives = np.array(Derivatives)
        Sum_Derivatives = np.array(Sum_Derivatives)
        Sum_Squared_Derivatives = np.array(Sum_Squared_Derivatives)
        self.nthModel['Signed_Feature_Importance'] = np.sign(Sum_Derivatives)*Sum_Squared_Derivatives/Sum_Squared_Derivatives.sum()

        # Scale Derivatives to original units
        v_X = self.Ensemble[nth]['X_scaler'].var_
        v_y = self.Ensemble[nth]['y_scaler'].var_
        Derivatives = Derivatives*(v_y**.5)/(v_X**.5)
        self.nthModel['Derivatives'] = Derivatives


        Best_ix = np.where(self.nthModel['Signed_Feature_Importance']==self.nthModel['Signed_Feature_Importance'].max())[0][0]
        Best_x =  X[Best_ix]

        # plt.figure()
        # plt.scatter(target,Prediction)
        print(self.Ensemble[nth]['RMSE'])
        
        plt.figure()
        plt.plot(self.Ensemble[nth]['X_scaler'].inverse_transform(X_values),Derivatives[Best_ix])

        plt.figure()
        plt.plot(self.Ensemble[nth]['X_scaler'].inverse_transform(X_values),self.Ensemble[nth]['y_scaler'].inverse_transform(target.reshape(1,-1)).flatten())
        plt.plot(self.Ensemble[nth]['X_scaler'].inverse_transform(X_values),self.Ensemble[nth]['y_scaler'].inverse_transform(Prediction.reshape(1,-1)).flatten())

        plt.show()
        breakpoint()



    
    
    def mlp_model(self,dataTable,X,y):
        train,test = self.test_train_split(dataTable)
        preprocessor = ColumnTransformer(
                transformers=[
                    ("Xscaler", StandardScaler(), X),
                ]
            )
        mlp_model = make_pipeline(
            preprocessor,
            MLPRegressor(
                hidden_layer_sizes=(self.hiddenLayerShape),
                learning_rate='adaptive',
                early_stopping=True,
                solver='lbfgs',
                activation=self.activation,
                verbose=True,
                n_iter_no_change=2,
                random_state=self.seed,
                max_iter=500
            ),
        )
        model = TransformedTargetRegressor(
            regressor=mlp_model,
            transformer=StandardScaler()
        )
        model.fit(train[X],train[y])

        breakpoint()
        mx = mlp_model.named_steps['mlpregressor']
        w_intercepts = mx.intercepts_
        w_weights = mx.coefs_
        print(mx.coefs_,mx.intercepts_)
        Output = []
        X_values = mlp_model.named_steps['columntransformer'].named_transformers_['scaler'].transform(dataTable[X])
        # Could replace this with model.predict() just doing for now to ensure I understand the math and can get the same answer as the model
        Zeros = np.zeros(w_intercepts[0].shape)
        for i in range(X_values.shape[0]):
            Input = X_values[i]
            H1 = (((Input*w_weights[0].T)).sum(axis=1)+w_intercepts[0])
            if mx.activation == 'relu':
                H1 = np.maximum(Zeros,H1)
            elif mx.activation == 'sigmoid':
                H1 = 1/(1+np.exp(-H1))
            elif mx.activation == 'tanh':
                H1 = np.tanh(H1)
            else:
                breakpoint()
            H2 = (H1*w_weights[1].T).sum()+w_intercepts[1]
            Output.append(H2)
        Output = np.array(Output)

        Target = dataTable[y].values

        # Get the derivatives
        Derivatives = []
        Sum_Derivatives = []
        Sum_Squared_Derivatives = []
        for i in range(X_values.shape[1]):
            dj = []
            for j in range (X_values.shape[0]):
                t = Target[j]
                o = Output[j]
                Xj = X_values[j,i]
                H1 = Xj*w_weights[0][i,:]+w_intercepts[0]
                H1 = np.maximum(Zeros,H1)
                # Calculate the derivative of the activation
                if mx.activation == 'relu':
                    H1 = np.maximum(Zeros,H1)
                    dH1 = np.zeros(H1.shape)
                    dH1[dH1>0]=1
                elif mx.activation == 'sigmoid':
                    dH1 = 1/(1+np.exp(-H1))
                    dH1 = dH1*(1-H1)
                elif mx.activation == 'tanh':
                    dH1 = 1-np.square(np.tanh(H1))
                else:
                    breakpoint()
                # Derivative of output (a linear function)
                Sj = 1
                Sigma = np.array([w_weights[1][h]*dH1[h]*w_weights[0][i,h] for h in range(w_weights[1].shape[0])]).sum()
                dj.append(Sj*Sigma)
            dji = np.array(dj)
            Derivatives.append(dj)
            Sum_Derivatives.append(np.sum(dji))
            Sum_Squared_Derivatives.append(np.sum(dji**2))

        Derivatives = np.array(Derivatives)
        Sum_Derivatives = np.array(Sum_Derivatives)
        Sum_Squared_Derivatives = np.array(Sum_Squared_Derivatives)

        Feature_Importance = Sum_Squared_Derivatives/Sum_Squared_Derivatives.sum()
        Signed_Importance = np.sign(Sum_Derivatives)

        Best_ix = np.where(Feature_Importance==Feature_Importance.max())[0][0]
        Best_x =  X[Best_ix]

        plt.figure()
        plt.scatter(Output,mlp_model.predict(dataTable[X]))

        plt.figure()
        plt.barh(X,Feature_Importance)
        
        print(Sum_Squared_Derivatives)
        plt.figure()
        plt.scatter(dataTable[X[Best_ix]],Derivatives[Best_ix])

        plt.show()
        breakpoint()

    




# dataTable = pd.read_csv(r'C:\Users\jskeeter\gsc-permafrost\pyFluxPipeline\testing\SCL_data.csv',parse_dates=[0],index_col=0)
# dataTable['Month'] = dataTable.index.month
# ensembleNN(hiddenLayerShape=(100),activation='relu').trainEnsemble(dataTable,X=['TA_1_1_1','SW_IN_1_1_1','Month'],y='TS_1_1_1')

Xar = np.arange(-10,10,1)
m = 1
b = 0
yar = m*Xar+b*np.random.random(Xar.shape)
yar[yar>0] = yar[yar>0]*2
data = pd.DataFrame(data={'X':Xar,'y':yar})
# plt.figure()
# plt.scatter(data['X'],data['y'])
# plt.title('Function')
# breakpoint()
ensembleNN(hiddenLayerShape=(5),activation='relu').trainEnsemble(data,X=['X'],y='y')
