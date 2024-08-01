import numpy as np
from numpy import ndarray
import statsmodels.api as sm
from .utils import *

import numpy as np
import statsmodels.api as sm

def drdid_rc(y: ndarray, post: ndarray, D: ndarray, covariates = None, i_weights = None):
  
  n = len(D)

  int_cov = np.ones(n)
  if covariates is not None:
    if np.all(covariates[:, 0] == int_cov):
      int_cov = covariates
    else:
      int_cov = np.concatenate((np.ones((n, 1)), covariates), axis=1)
  pscore_tr = glm(D, int_cov, family=binomial, freq_weights=i_weights)\
    .fit()

  ps_fit, w_cont_pre, _,\
    w_cont_post, _, asy_lin_rep_ps = fit_ps(D, int_cov, i_weights, post)
  
  def reg_out_y(d, p, y = y, int_cov = int_cov, wg = i_weights):
    rows_ = (D == d) & (post == p)
    reg_cont = lm(y[rows_], int_cov[rows_], weights=wg[rows_])\
      .fit().params
    out_y = np.dot(reg_cont, int_cov.T)
    return out_y


  out_y_cont_pre = reg_out_y(d = 0, p = 0)
  out_y_cont_post = reg_out_y(d = 0, p = 1)
  out_y_cont = post * out_y_cont_post + (1 - post) * out_y_cont_pre 

  out_y_treat_pre = reg_out_y(d = 1, p = 0)
  out_y_treat_post = reg_out_y(d = 1, p = 1)

  w_treat_pre = i_weights * D * (1 - post)
  w_treat_post = i_weights * D * post
  rest_cont = i_weights * ps_fit * (1 - D) 

  w_d = i_weights * D
  w_dt1 = w_d * post
  w_dt0 = w_d * (1 - post)

  def eta_treat(a, b = out_y_cont, y = y):
    return a * (y - b) / np.mean(a)

  eta_treat_pre = eta_treat(w_treat_pre)
  eta_treat_post = eta_treat(w_treat_post)
  eta_cont_pre = eta_treat(w_cont_pre)
  eta_cont_post = eta_treat(w_cont_post)

  eta_d_post = eta_treat(w_d, out_y_cont_post, out_y_treat_post)
  eta_d_pre = eta_treat(w_d, out_y_cont_pre, out_y_treat_pre)
  eta_dt1_post = eta_treat(w_dt1, out_y_cont_post, out_y_treat_post)
  eta_dt0_pre = eta_treat(w_dt0, out_y_cont_pre, out_y_treat_pre)

  att_treat_pre = np.mean(eta_treat_pre)
  att_treat_post = np.mean(eta_treat_post)
  att_cont_pre = np.mean(eta_cont_pre)
  att_cont_post = np.mean(eta_cont_post)

  att_d_post = np.mean(eta_d_post)
  att_dt1_post = np.mean(eta_dt1_post)
  att_d_pre = np.mean(eta_d_pre)
  att_dt0_pre = np.mean(eta_dt0_pre)


  dr_att = (att_treat_post - att_treat_pre) - \
    (att_cont_post - att_cont_pre) -\
    (att_d_post - att_dt1_post) -\
    (att_d_pre - att_dt0_pre)
  def asy_lin_wols(d, post, out_y, int_cov = int_cov):
    weigths_ols = i_weights * d * post
    # weigths_ols_pre
    wols_x = weigths_ols[:, n_x] * int_cov
    wols_ex = (weigths_ols * (y - out_y))[:, n_x] * int_cov
    cr = np.dot(wols_x.T, int_cov) / n
    xpx_inv = qr_solver(cr)
    asy_lin_rep_ols = np.dot(wols_ex, xpx_inv)
    return asy_lin_rep_ols

  asy_lin_rep_ols_pre = asy_lin_wols((1 - D), (1 - post), out_y_cont_pre)
  asy_lin_rep_ols_post = asy_lin_wols((1 - D), post, out_y_cont_post)

  asy_lin_rep_ols_pre_treat = asy_lin_wols(
    D, (1 - post), out_y_treat_pre
  )
  asy_lin_rep_ols_post_treat = asy_lin_wols(D, post, out_y_treat_post)


  inf_treat_pre = eta_treat_pre - w_treat_pre * att_treat_pre\
    / np.mean(w_treat_pre)
  inf_treat_post = eta_treat_post - w_treat_post * att_treat_post\
    / np.mean(w_treat_post)

  M1_post = np.mean((w_treat_post * post)[:, n_x] * int_cov, axis=0) / np.mean(w_treat_post)
  M1_pre = np.mean((w_treat_pre * (1 - post))[:, n_x] * int_cov, axis=0) / np.mean(w_treat_pre)

  inf_treat_or_post = np.dot(asy_lin_rep_ols_post, M1_post)
  inf_treat_or_pre = np.dot(asy_lin_rep_ols_pre, M1_pre)
  inf_treat_or = inf_treat_or_post - inf_treat_or_pre

  inf_treat = inf_treat_post - inf_treat_pre + inf_treat_or

  inf_cont_pre = eta_cont_pre - w_cont_pre * att_cont_pre / np.mean(w_cont_pre)
  inf_cont_post = eta_cont_post - w_cont_post * att_cont_post / np.mean(w_cont_post)

  M2_pre = np.mean(
    ((w_cont_pre * (y - out_y_cont - att_cont_pre))[:, n_x] * int_cov), 
    axis=0
  ) / np.mean(w_cont_pre)
  M2_post = np.mean(
    ((w_cont_post * (y - out_y_cont - att_cont_post))[:, n_x] * int_cov),
    axis=0
  ) / np.mean(w_cont_post)

  inf_cont_ps = np.dot(asy_lin_rep_ps, M2_post - M2_pre)

  M3_post = np.mean(
    (w_cont_post * post)[:, n_x] * int_cov, axis=0
  ) / np.mean(w_cont_post)
  M3_pre = np.mean(
    (w_cont_pre * (1 - post))[:, n_x] * int_cov, axis=0
  ) / np.mean(w_cont_pre)

  inf_cont_or_post = np.dot(asy_lin_rep_ols_post, M3_post)
  inf_cont_or_pre = np.dot(asy_lin_rep_ols_pre, M3_pre)
  inf_cont_or = inf_cont_or_post - inf_cont_or_pre

  inf_cont = inf_cont_post - inf_cont_pre + inf_cont_ps + inf_cont_or

  dr_att_inf_func1 = inf_treat - inf_cont

  def inf_eff_f(a, b, c):
    return a - b * c / np.mean(b)

  inf_eff1 = inf_eff_f(eta_d_post, w_d, att_d_post)
  inf_eff2 = inf_eff_f(eta_dt1_post, w_dt1, att_dt1_post)
  inf_eff3 = inf_eff_f(eta_d_pre, w_d, att_d_pre)
  inf_eff4 = inf_eff_f(eta_dt0_pre, w_dt0, att_dt0_pre)
  inf_eff = inf_eff1 - inf_eff2 - (inf_eff3 - inf_eff4)

  def mom_f(a, b, int_cov = int_cov):
    left = a / np.mean(a) - b / np.mean(b)
    return np.mean(left[:, n_x] * int_cov, axis=0) 

  mom_post = mom_f(w_d, w_dt1)
  mom_pre = mom_f(w_d, w_dt0)

  inf_or_post = np.dot(
    asy_lin_rep_ols_post_treat - asy_lin_rep_ols_post, 
    mom_post
  )
  inf_or_pre = np.dot(
    asy_lin_rep_ols_pre_treat - asy_lin_rep_ols_pre, 
    mom_pre
  )
  inf_or = inf_or_post - inf_or_pre
  dr_att_inf_func = dr_att_inf_func1 + inf_eff + inf_or

  return (dr_att, dr_att_inf_func)


def drdid_panel(y1, y0, D, covariates, i_weights=None, boot=False, boot_type="weighted", nboot=None, inffunc=False):
    # Convert inputs to numpy arrays
    D = np.asarray(D).flatten()
    n = len(D)
    deltaY = np.asarray(y1 - y0).flatten()
    
    # Add constant to covariate matrix
    if covariates is None:
        int_cov = np.ones((n, 1))
    else:
        covariates = np.asarray(covariates)
        if np.all(covariates[:, 0] == 1):
            int_cov = covariates
        else:
            int_cov = np.column_stack((np.ones(n), covariates))
    
    # Weights
    if i_weights is None:
        i_weights = np.ones(n)
    elif np.min(i_weights) < 0:
        raise ValueError("i_weights must be non-negative")
    
    # Normalize weights
    i_weights = i_weights / np.mean(i_weights)
    # print(D.mean())
    
    # Compute the Pscore by MLE
    pscore_model = sm.GLM(D, int_cov, family=sm.families.Binomial(), freq_weights=i_weights)
    pscore_results = pscore_model.fit()
    # print(D.mean())
    # print(pscore_results.summary2())
    if not pscore_results.converged:
        print("Warning: glm algorithm did not converge")
    if np.any(np.isnan(pscore_results.params)):
        raise ValueError("Propensity score model coefficients have NA components. \n Multicollinearity (or lack of variation) of covariates is a likely reason.")
    ps_fit = pscore_results.predict()
    ps_fit = np.minimum(ps_fit, 1 - 1e-16)
    # print(ps_fit)
    
    # Compute the Outcome regression for the control group using wols
    mask = D == 0
    reg_model = sm.WLS(deltaY[mask], int_cov[mask], weights=i_weights[mask])
    reg_results = reg_model.fit()
    if np.any(np.isnan(reg_results.params)):
        raise ValueError("Outcome regression model coefficients have NA components. \n Multicollinearity (or lack of variation) of covariates is a likely reason.")
    out_delta = np.dot(int_cov, reg_results.params)
    
    # Compute Traditional Doubly Robust DiD estimators
    w_treat = i_weights * D
    w_cont = i_weights * ps_fit * (1 - D) / (1 - ps_fit)
    dr_att_treat = w_treat * (deltaY - out_delta)
    dr_att_cont = w_cont * (deltaY - out_delta)
    
    eta_treat = np.mean(dr_att_treat) / np.mean(w_treat)
    eta_cont = np.mean(dr_att_cont) / np.mean(w_cont)
    
    dr_att = eta_treat - eta_cont
    
    # Compute influence function
    weights_ols = i_weights * (1 - D)
    wols_x = weights_ols[:, np.newaxis] * int_cov
    wols_eX = weights_ols[:, np.newaxis] * (deltaY - out_delta)[:, np.newaxis] * int_cov
    XpX_inv = np.linalg.inv(np.dot(wols_x.T, int_cov) / n)
    asy_lin_rep_wols = np.dot(wols_eX, XpX_inv)
    
    score_ps = i_weights[:, np.newaxis] * (D - ps_fit)[:, np.newaxis] * int_cov
    Hessian_ps = pscore_results.cov_params() * n
    asy_lin_rep_ps = np.dot(score_ps, Hessian_ps)
    
    inf_treat_1 = dr_att_treat - w_treat * eta_treat
    M1 = np.mean(w_treat[:, np.newaxis] * int_cov, axis=0)
    inf_treat_2 = np.dot(asy_lin_rep_wols, M1)
    inf_treat = (inf_treat_1 - inf_treat_2) / np.mean(w_treat)
    
    inf_cont_1 = dr_att_cont - w_cont * eta_cont
    M2 = np.mean(w_cont[:, np.newaxis] * (deltaY - out_delta - eta_cont)[:, np.newaxis] * int_cov, axis=0)
    inf_cont_2 = np.dot(asy_lin_rep_ps, M2)
    M3 = np.mean(w_cont[:, np.newaxis] * int_cov, axis=0)
    inf_cont_3 = np.dot(asy_lin_rep_wols, M3)
    inf_control = (inf_cont_1 + inf_cont_2 - inf_cont_3) / np.mean(w_cont)
    
    dr_att_inf_func = inf_treat - inf_control
    
    return dr_att, dr_att_inf_func


  
