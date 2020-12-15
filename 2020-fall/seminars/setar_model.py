"""
Self-Exciting Threshold Autoregression

References
----------

Hansen, Bruce. 1999.
"Testing for Linearity."
Journal of Economic Surveys 13 (5): 551-576.
"""

from __future__ import division
import numpy as np
import statsmodels.tsa.base.tsa_model as tsbase
from statsmodels.tsa.tsatools import lagmat
from statsmodels.tools.tools import add_constant
from statsmodels.regression.linear_model import OLS

class SETAR(tsbase.TimeSeriesModel):
    """
    Self-Exciting Threshold Autoregressive Model

    Parameters
    ----------
    endog : array-like
        The endogenous variable.
    order : integer
        The order of the SETAR model, indication the number of regimes.
    ar_order : integer
        The order of the autoregressive parameters.
    delay : integer, optional
        The delay for the self-exciting threshold variable.
    thresholds : iterable, optional
        The threshold values separating the data into regimes.
    min_regime_frac : scalar, optional
        The minumum fraction of observations in each regime.
    max_delay : integer, optional
        The maximum delay parameter to consider if a grid search is used. If
        left blank, it is set to be the ar_order.
    threshold_grid_size : integer, optional
        The number of elements in the threshold grid if a grid search is used.

    Notes
    -----

    """

    # TODO are there too many parameters here?
    def __init__(self, endog, order, ar_order,
                    delay=None, thresholds=None, min_regime_frac = 0.1, max_delay=None, 
                    threshold_grid_size=100,
                    dates=None, freq=None, missing='none'):
        super(SETAR, self).__init__(endog, None, dates, freq)

        if delay < 1 or delay >= len(endog):
            raise ValueError('Delay parameter must be greater than zero' \
                                ' and less than nobs. Got %d.' % delay
                            )

        if thresholds is not None and not len(thresholds)+1 == order:
            raise ValueError("Number of thresholds must match"\
                " the order of the SETAR model")

        # "Immutable" properties
        self.order = order
        self.k_ar = ar_order
        self.min_regime_frac = min_regime_frac
        self.max_delay = max_delay if max_delay is not None else ar_order
        self.threshold_grid_size = threshold_grid_size

        # "Flexible" properties
        self.delay = delay
        # TODO I sort in case thresholds are in wrong order, but that seems
        #      like it may be wasteful, since it won't usually be the case?
        #      and feels like user error anyway...
        self.thresholds = np.sort(thresholds)
        self.regimes = None
        
    def _get_regime_indicators(self, delay, thresholds):
        """
        Generate an indicator vector of regimes (0, ..., order-1)
        """
        return np.r_[
                [np.NaN]*delay,
                np.searchsorted(self.thresholds, self.endog[:-delay])
            ]

    def fit(self):
        """
        Fits SETAR() model using arranged autoregression.

        Returns
        -------
        statsmodels.tsa.arima_model.SETARResults class

        See also
        --------
        statsmodels.regression.linear_model.OLS : this estimates each regime
        SETARResults : results class returned by fit

        """

        if self.delay is None or self.thresholds is None:
            self.delay, self.thresholds = self.select_hyperparameters()

        nobs_initial = max(self.k_ar, self.delay)
        nobs = len(self.endog) - nobs_initial

        indicators = self._get_regime_indicators(self.delay, self.thresholds)
        indicator_matrix = (indicators[:,None]==range(self.order))

        lags = add_constant(lagmat(self.endog, self.k_ar))

        # TODO this seems like probably not the best way...
        #      e.g. for large order (although not common) this will be big, and
        #      maybe some kind of sparse matrix would be more efficient?
        exog = np.multiply(
                    np.bmat('lags '*self.order),
                    np.kron(indicator_matrix, np.ones(self.k_ar+1))
                )[nobs_initial:, :]
        endog = self.endog[nobs_initial:,]

        # Make sure each regime has enough datapoints
        if indicator_matrix.sum(0).min() < np.ceil(nobs*self.min_regime_frac):
            # TODO is this the right exception to throw?
            raise ValueError('Regime %d has too few observations:' \
                                ' threshold values may need to be adjusted' %
                                indicator_matrix.sum(0).argmin()
                            )

        # TODO implement the SETARResults class to nicely show all
        #      regimes' results
        # TODO really just doing OLS on this dataset...is there a better way to
        #      do this?
        return OLS(endog, exog).fit()

    def select_hyperparameters(self):
        """
        Select delay and threshold hyperparameters via grid search
        """

        raise NotImplementedError

        return delay, thresholds


    # TODO should we allow selecting the AR order based on IC? 
    #      Probably not, because it adds another dimension to the search space
    #      (i.e. delay x threshold x ar_order), and in any case higher order
    #      AR models are flexible enough to capture many non-linear dynamics,
    #      so I don't think we can algorithmically identify for people whether
    #      e.g. an AR(6) or a SETAR(2) is more appropriate.
    #      
    #      However, if we do want to, one approach is just to use information
    #      criteria to select the order of an AR model, exactly as done in the
    #      select_order() method of ARModel()
    def select_order(self):
        raise NotImplementedError

'''
class SETARResults:
    pass

if __name__ == '__main__':
    
    import pandas as pd
    import statsmodels.api as sm

    dta = sm.datasets.sunspots.load_pandas().data
    dta.index = pd.Index(sm.tsa.datetools.dates_from_range('1700', '2008'))
    dta = dta[dta.YEAR <= 1988]
    del dta["YEAR"]

    dta.SUNACTIVITY = 2*(np.sqrt(1 + dta.SUNACTIVITY) - 1)

    mod = SETAR(dta, order=2, delay=2, ar_order=11, thresholds=(7.43,))
    res = mod.fit()

    print res.summary()
'''

'''
Hansen (1999) - Table 2:

        coef    std err
X1      -0.58   0.9
X2      1.22    0.1
X3      -0.97   0.26
X4      0.49    0.29
X5      -0.19   0.26
X6      -0.14   0.28
X7      0.12    0.26
X8      0.13    0.21
X9      -0.22   0.23
X10     0.46    0.26
X11     -0.07   0.2
X12     -0.07   0.12
X13     2.32    0.55
X14     0.95    0.08
X15     -0.03   0.11
X16     -0.48   0.1
X17     0.32    0.09
X18     -0.21   0.08
X19     -0.04   0.08
X20     0.18    0.08
X21     -0.22   0.09
X22     0.19    0.09
X23     -0.02   0.09
X24     0.12    0.07

'''