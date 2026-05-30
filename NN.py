import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler # OneHotEncoder, QuantileTransformer,
from sklearn.compose import TransformedTargetRegressor
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
    
    def trainEnsemble(self,dataTable,X,y):
        ix = (~dataTable[X+[y]].isna()).all(axis=1) 
        self.Ensemble = {}
        for i in range(self.nModels):
            self.model = {}
            self.seed += i
            self.trainModel(dataTable.loc[ix,X+[y]],X,y)
            self.Ensemble[i] = self.model


    def trainModel(self,dataTable,X,y):
        train,test = self.test_train_split(dataTable,X,y,scale=True)
        # train,test = self.scaleVariables(train,test,X,y)
        breakpoint()

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
        Xs,ys = StandardScaler(),StandardScaler()
        Xs.fit(train[X])
        ys.fit(train[y])
        self.model['X_scaler'] = Xs
        self.model['y_scaler'] = ys
        train[X] = Xs.transform(train[X])
        test[X] = Xs.transform(test[X])
        train[y] = ys.transform(train[y])
        test[y] = ys.transform(test[y])
        return(train,test)



    
    def y_norm(self,y_values,reverse=False):
        if not reverse:
            self.y_mu = y_values.mean()
            self.y_sigma = y_values.std()
            y_values = (y_values-self.y_mu)/self.y_sigma
        else:
            y_values = y_values*self.y_sigma+self.y_mu
        return(y_values)
    
    
    
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
                    dH1 = np.maximum(Zeros,H1)
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

    




def MPL_reg(df,X,y,n=5,nl=25,est=None):    
    Scores = []
    ds = df[ X + [y]].dropna().copy()
    # exit()
    df[f"{y}_pred"] = np.nan
    df.loc[df[X].notnull().all(axis=1), f"{y}_pred"] = 0
    if est is not None:
        est[f"{y}_pred"] = 0
    # print(X)
    # print(df.shape,df.loc[df[X].notnull().all(axis=1), X].shape)
    for seed in range(n):
        mlp_preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), X),
            ]
        )
        train,test = test_train(ds,seed=seed,test_size=0.1)
        mlp_model = make_pipeline(
            mlp_preprocessor,
            MLPRegressor(
                hidden_layer_sizes=(nl),
                # learning_rate_init='adaptive',
                early_stopping=True,
                solver='lbfgs',
                activation='relu',
                verbose=True,
                n_iter_no_change=2,
                random_state=seed,
                max_iter=2000
            ),
        )
        
        mlp_model.fit(train[X],train[y])
        mx = mlp_model.named_steps['mlpregressor']
        print(mx.coefs_,mx.intercepts_)
        if y.startswith('FCH4'):
            df.loc[df[X].notnull().all(axis=1), f'{y}_pred'] += mlp_model.predict(df.loc[df[X].notnull().all(axis=1), X])*std_ch4+mean_ch4
            if est is not None: 
                est[f'{y}_pred_{seed}'] = mlp_model.predict(est[X])*std_ch4+mean_ch4
        else:
            df.loc[df[X].notnull().all(axis=1), f'{y}_pred'] += mlp_model.predict(df.loc[df[X].notnull().all(axis=1), X])*std_co2+mean_co2
            
            if est is not None: 
                est[f'{y}_pred_{seed}'] = mlp_model.predict(est[X])*std_co2+mean_co2
        # print(f"done in {time() - tic:.3f}s")
        score = mlp_model.score(test[X],test[y])
        Scores.append(score)
    df[f"{y}_pred"] /= n
    if est is not None:
        est[f"{y}_pred"] /= n
    print(f"Test R2 score: {np.median(np.array(Scores)):.2f}")
    return(df,n,est)


dataTable = pd.read_csv(r'C:\Users\jskeeter\gsc-permafrost\pyFluxPipeline\testing\SCL_data.csv',parse_dates=[0],index_col=0)
ensembleNN(hiddenLayerShape=(10),activation='tanh').trainEnsemble(dataTable,X=['TA_1_1_1','SW_IN_1_1_1'],y='TS_1_1_1')
