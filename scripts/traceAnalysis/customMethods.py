import numpy as np
import pandas as pd
# Any function here will be available for execution within the evaluate statements

class customMethods:    

    def __init__(self):
        pass

    def Ps_buck(self,TA,RH):
        Tpos = np.where(TA>=0)[0]
        Tneg = np.where(TA<0)[0]

        Ps_posT=6.1121*np.exp((18.678-TA/234.5)*(TA/(257.14+TA)))
        Ps_negT=6.1115*np.exp((23.036-TA/333.7)*(TA/(279.82+TA)))

        Ps = TA*np.nan
        Ps[Tpos] = Ps_posT[Tpos]
        Ps[Tneg] = Ps_negT[Tneg]
        Pv = Ps*RH/100    
        return (Pv,Ps)

    def Ps_stull(self,TA,RH):
        #  Reference 
        #  Stull, 2017: Practical Meteorology, pp.89-92
        # 
        #  Output:   Pv = vapour pressure in kPa
        #            Ps = saturated vapour pressure in kPa

        #  constants
        Rv = 461    # water vapour gas constant (J kg^-1 K^-1)
        T0 = 273.15 # reference temperature (K)
        e0 = 0.6113 # reference vapour pressure (kPa)
        Lv = 2.5e6  # latent heat of vaporization (J kg^-1)
        Ld = 2.83e6 # latent heat of deposition (J kg^-1) 

        T_K = TA + 273.15    # convert temperature to Kelvin

        # calculate vapour pressure (kPa)
        Ps = e0*np.exp((Lv/Rv) * ((1/T0) - (T_K**(-1)) ))     # Clausius-Clapeyron eqn.
        Pv = Ps*RH/100
        return(Pv,Ps)

    #  EOF

    def calculateVPD(self,TA,RH,method='Buck'):
        if isinstance(TA,pd.Series):
            TA = TA.values
        if isinstance(RH,pd.Series):
            RH = RH.values
        method = method.lower()
        if method == 'buck':
            Pv,Ps = self.Ps_buck(TA,RH)
        elif method == 'stull':
            Pv,Ps = self.Ps_stull(TA,RH)

        VPD = Ps-Pv
        if method == 'Stull':
            VPD = VPD*10
        VPD[VPD < 0] = 0   

        return(VPD)

# TA,RH = (np.random.random(100)-.25)*10,np.random.random(100)*100
# Buck = VPD(TA,RH,method='Buck')
# Stull = VPD(TA,RH,method='Stull')

# print(np.mean(Buck-Stull))
# print(VPD((np.random.random(10)-.25)*10,np.random.random(10)*0+100))