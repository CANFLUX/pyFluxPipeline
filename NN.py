import pandas as pd
import numpy as np
import math
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler # OneHotEncoder, QuantileTransformer,
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import r2_score,mean_squared_error,mean_absolute_error
from scipy import stats
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

@dataclass(kw_only=True)
class inputData(defaultSettings):
    X: list
    y: str


class ensembleNN(inputData):
    # Train an ensemble of (single layer default) Dense Feed Forward Neural Networks
    # Scales data (without using pipeline mode) for increased flexibility and transparency
    # Trains NN (early stopping using validation set)
    # Evaluates model to get the test score (mean & 95% CI from ensemble)
    # From ensemble, calculates mean prediction and 95%CI from variance of estimates
    # Calculates partial derivatives (using test data) to:
    #   1. Evaluate feature importance with Sum of Squared Derivatives (and sign)
    #   2. Map response functions over feature space
    #   3. Get confidence in response from ensemble mean and CI
    
    
    def trainEnsemble(self,dataTable):
        self.Ensemble = {}
        self.ix = (~dataTable[self.X+[self.y]].isna()).all(axis=1) 
        for nth in range(self.nModels):
            self.nthModel = {}
            self.seed += nth
            dataTable[f"{self.y}_ANN_f_{nth}"] = np.nan
            dataTable.loc[self.ix,f"{self.y}_ANN_f_{nth}"] = self.trainModel(dataTable.loc[self.ix,self.X+[self.y]])
            self.Ensemble[nth] = self.nthModel
        self.evaluateEnsemble(dataTable.loc[self.ix,self.X+[self.y]])

    def evaluateEnsemble(self,dataTable):
        self.featureSpace = dataTable        
        for nth in range(self.nModels):
            self.calculateDerivatives(nth,dataTable.copy())
        self.plotEvaluation()

    def trainModel(self,dataTable):
        # Split and scale the data for each model
        train,test = self.test_train_split(dataTable,scale=True)
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
        model.fit(train[self.X],train[self.y])
        test_prediction = model.predict(test[self.X])
        self.nthModel['R2'] = r2_score(test[self.y],test_prediction)
        self.nthModel['RMSE'] = mean_squared_error(test[self.y],test_prediction)**.5
        self.nthModel['MAE'] = mean_absolute_error(test[self.y],test_prediction)
        self.nthModel['MLPRegressor'] = model
        return(model.predict(dataTable[self.X]))

    def test_train_split(self,dataTable,scale):
        # Split out the test set
        np.random.seed(self.seed)
        test_size = int(dataTable.shape[0]*self.test_split)
        test_set = np.random.randint(0, dataTable.shape[0],test_size)
        test_set = dataTable.iloc[test_set,:].copy()
        train_set = dataTable.loc[~dataTable.index.isin(test_set.index),:].copy()
        if scale == True:
            train_set,test_set = self.scaleVariables(train_set,test_set)
            return (train_set,test_set)    
        else:
            return (train_set,test_set)
        
    def scaleVariables(self,train,test):
        # Scale train[X], test[X] and train[y], test[y] by only the training set
        # For now just numeric, can add categorical later
        Xs,ys = StandardScaler(),StandardScaler()
        Xs.fit(train[self.X])
        ys.fit(train[[self.y]])
        self.nthModel['X_scaler'] = Xs
        self.nthModel['y_scaler'] = ys
        train[self.X] = Xs.transform(train[self.X])
        test[self.X] = Xs.transform(test[self.X])
        train[self.y] = ys.transform(train[[self.y]])
        test[self.y] = ys.transform(test[[self.y]])
        return(train,test)

    def calculateDerivatives(self,nth,featureSpace):
        featureSpace[self.X] = self.Ensemble[nth]['X_scaler'].transform(featureSpace[self.X])
        # featureSpace[y] = self.Ensemble[nth]['y_scaler'].transform(featureSpace[[y]])
        # Get the model derivatives over the feature space for the nth model in the ensemble
        self.nthModel = self.Ensemble[nth]
        model = self.nthModel['MLPRegressor']
        X_values = featureSpace[self.X].values
        target = featureSpace[self.y].values
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
        self.nthModel['featureImportance'] = Sum_Squared_Derivatives/Sum_Squared_Derivatives.sum()
        
        # Scale Derivatives to original units of X & y
        sigma_X = self.Ensemble[nth]['X_scaler'].var_**.5
        sigma_y = self.Ensemble[nth]['y_scaler'].var_**.5
        Derivatives = Derivatives.T*(sigma_y)/(sigma_X)
        self.nthModel['partialDerivatives'] = Derivatives


    def plotEvaluation(self):
        featureImportance = pd.DataFrame(index=self.X,data={str(nth):values['featureImportance'] for nth,values in self.Ensemble.items()})
        self.featureImportance = pd.DataFrame(index=self.X,data={'mean':featureImportance.mean(axis=1),'SE':featureImportance.std(axis=1)/(self.nModels**.5)})

        self.featureImportance = self.featureImportance.sort_values(by='mean')
        plt.figure()
        plt.barh(self.featureImportance.index,self.featureImportance['mean'],yerr=self.featureImportance['SE'])
        dy_dx = np.array([values['partialDerivatives'] for values in self.Ensemble.values()])
        dy_dx_mean = dy_dx.mean(axis=0)
        dy_dx_CI = dy_dx.std(axis=0)/(self.nModels**.5)*stats.t.ppf(0.975,self.nModels)
        rows = math.ceil(len(self.X)**.5)
        cols = round(len(self.X)**.5)
        fig = plt.figure()
        fig2 = plt.figure()
        for n,x in enumerate(self.X):
            if n == 0:
                ax = fig.add_subplot(rows,cols,n+1)
                ax2 = fig2.add_subplot(rows,cols,n+1)
            else:
                ax = fig.add_subplot(rows,cols,n+1,sharey=ax)
                ax2 = fig2.add_subplot(rows,cols,n+1,sharey=ax2)

            ax2.scatter(self.featureSpace[x],self.featureSpace[self.y])

            df = pd.DataFrame(
                index=self.featureSpace[x],
                data={
                    'mean':dy_dx_mean[:,n],
                    'lower':dy_dx_mean[:,n]-dy_dx_CI[:,n],
                    'upper':dy_dx_mean[:,n]+dy_dx_CI[:,n]
                    }
                )
            df = df.sort_index()
            ax.plot(df.index,df['mean'],color='red')
            ax.fill_between(df.index,df['lower'],df['upper'],edgecolor='blue',facecolor=(0.0, 0.0, 1.0, 0.5))
            ax.set_title(x)
        plt.tight_layout()
        plt.show()




# dataTable = pd.read_csv(r'C:\Users\jskeeter\gsc-permafrost\pyFluxPipeline\testing\SCL_data.csv',parse_dates=[0],index_col=0)
# dataTable['Month'] = dataTable.index.month
# ensembleNN(hiddenLayerShape=(100),activation='relu').trainEnsemble(dataTable,X=['TA_1_1_1','SW_IN_1_1_1','Month'],y='TS_1_1_1')

# breakpoint()
nobs = 101
I = 10
X1 = np.concat([np.linspace(-10,10,nobs) for i in range(I)])
X2 = np.concat([np.linspace(-1,1,nobs)*i+1 for i in range(I)])
X3 = np.random.random(X1.shape)
# X2[X2<0]=0
a = 1
b = 1
c = 1
yar = a*X1**2+b*X2 +c*X3
# yar[yar>1] = yar[yar>1]*2
data = pd.DataFrame(data={'X1':X1,'X2':X2,'X3':X3,'y':yar})
data = data.sort_values(by='X1')
# print(data)
eNN = ensembleNN(hiddenLayerShape=(10),activation='relu',nModels=10,X=['X1','X2','X3'],y='y')
eNN.trainEnsemble(data)

# breakpoint()