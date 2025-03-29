#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import sys, os, time, json, datetime,subprocess,copy
import smbus


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "sgp40"


import time
import sys



VOCALGORITHM_SAMPLING_INTERVAL                           = (1.)
VOCALGORITHM_INITIAL_BLACKOUT                            = (45.)
VOCALGORITHM_VOC_INDEX_GAIN                              = (230.)
VOCALGORITHM_SRAW_STD_INITIAL                            = (50.)
VOCALGORITHM_SRAW_STD_BONUS                              = (220.)
VOCALGORITHM_TAU_MEAN_VARIANCE_HOURS                     = (12.)
VOCALGORITHM_TAU_INITIAL_MEAN                            = (20.)
VOCALGORITHM_INITI_DURATION_MEAN                         = (3600. * 0.75)
VOCALGORITHM_INITI_TRANSITION_MEAN                       = (0.01)
VOCALGORITHM_TAU_INITIAL_VARIANCE                        = (2500.)
VOCALGORITHM_INITI_DURATION_VARIANCE                     = ((3600. * 1.45))
VOCALGORITHM_INITI_TRANSITION_VARIANCE                   = (0.01)
VOCALGORITHM_GATING_THRESHOLD                            = (340.)
VOCALGORITHM_GATING_THRESHOLD_INITIAL                    = (510.)
VOCALGORITHM_GATING_THRESHOLD_TRANSITION                 = (0.09)
VOCALGORITHM_GATING_MAX_DURATION_MINUTES                 = ((60. * 3.))
VOCALGORITHM_GATING_MAX_RATIO                            = (0.3)
VOCALGORITHM_SIGMOID_L                                   = (500.)
VOCALGORITHM_SIGMOID_K                                   = (-0.0065)
VOCALGORITHM_SIGMOID_X0                                  = (213.)
VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT                    = (100.)
VOCALGORITHM_LP_TAU_FAST                                 = (20.0)
VOCALGORITHM_LP_TAU_SLOW                                 = (500.0)
VOCALGORITHM_LP_ALPHA                                    = (-0.2)
VOCALGORITHM_PERSISTENCE_UPTIME_GAMMA                    = ((3. * 3600.))
VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING      = (64.)
VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX          = (32767.)
FIX16_MAXIMUM                                            = 0x7FFFFFFF
FIX16_MINIMUM                                            = 0x80000000
FIX16_OVERFLOW                                           = 0x80000000
FIX16_ONE                                                = 0x00010000

class DFRobot_vocalgorithmParams:
	def __init__(self):
		self.mvoc_index_offset = 0
		self.mtau_mean_variance_hours = 0
		self.mgating_max_duration_minutes = 0
		self.msraw_std_initial=0
		self.muptime=0
		self.msraw=0
		self.mvoc_index=0
		self.m_mean_variance_estimator_gating_max_duration_minutes=0
		self.m_mean_variance_estimator_initialized=0
		self.m_mean_variance_estimator_mean=0
		self.m_mean_variance_estimator_sraw_offset=0
		self.m_mean_variance_estimator_std=0
		self.m_mean_variance_estimator_gamma=0
		self.m_mean_variance_estimator_gamma_initial_mean=0
		self.m_mean_variance_estimator_gamma_initial_variance=0
		self.m_mean_variance_estimator_gamma_mean=0
		self.m_mean_variance_estimator__gamma_variance=0
		self.m_mean_variance_estimator_uptime_gamma=0
		self.m_mean_variance_estimator_uptime_gating=0
		self.m_mean_variance_estimator_gating_duration_minutes=0
		self.m_mean_variance_estimator_sigmoid_l=0
		self.m_mean_variance_estimator_sigmoid_k=0
		self.m_mean_variance_estimator_sigmoid_x0=0
		self.m_mox_model_sraw_mean=0
		self.m_sigmoid_scaled_offset=0
		self.m_adaptive_lowpass_a1=0
		self.m_adaptive_lowpass_a2=0
		self.m_adaptive_lowpass_initialized=0
		self.m_adaptive_lowpass_x1=0
		self.m_adaptive_lowpass_x2=0
		self.m_adaptive_lowpass_x3=0

class DFRobot_VOCAlgorithm:
	
	def __init__(self):
		self.params = DFRobot_vocalgorithmParams()
	def _f16(self,x):
		if x >= 0:
			return int((x)*65536.0 + 0.5)
		else:
			return int((x)*65536.0 - 0.5)

	def _fix16_from_int(self,a):
		return int(a * FIX16_ONE)

	def _fix16_cast_to_int(self,a):
		return int(a) >> 16

	def _fix16_mul(self,inarg0,inarg1):
		inarg0=int(inarg0)
		inarg1=int(inarg1)
		A = (inarg0 >> 16)
		if inarg0<0:
			B = (inarg0&0xFFFFFFFF) & 0xFFFF
		else:
			B = inarg0&0xFFFF
		C = (inarg1 >> 16)
		if inarg1<0:
			D = (inarg1&0xFFFFFFFF) & 0xFFFF
		else:
			D = inarg1&0xFFFF
		AC = (A * C)
		AD_CB = (A * D + C * B)
		BD = (B * D)
		product_hi = (AC + (AD_CB >> 16))
		ad_cb_temp = ((AD_CB) << 16)&0xFFFFFFFF
		product_lo = ((BD + ad_cb_temp))&0xFFFFFFFF
		if product_lo < BD :
			product_hi =product_hi+1
		if ((product_hi >> 31) != (product_hi >>15)):
			return FIX16_OVERFLOW
		product_lo_tmp = product_lo&0xFFFFFFFF
		product_lo = (product_lo - 0x8000)&0xFFFFFFFF
		product_lo = (product_lo-((product_hi&0xFFFFFFFF) >> 31))&0xFFFFFFFF
		if product_lo > product_lo_tmp:
			product_hi = product_hi-1
		result = (product_hi << 16)|(product_lo >> 16)
		result +=1
		return result
	
	def _fix16_div(self,a, b):
		a=int(a)
		b=int(b)
		if b==0 :
			return FIX16_MINIMUM
		if a>=0:
			remainder = a
		else:
			remainder = (a*(-1))&0xFFFFFFFF
		if b >= 0:
			divider = b
		else:
			divider = (b*(-1))&0xFFFFFFFF
		quotient = 0
		bit =0x10000
		while (divider < remainder):
			divider = divider<<1
			bit <<= 1
		if not bit:
			return FIX16_OVERFLOW
		if (divider & 0x80000000):
			if (remainder >= divider):
				quotient |= bit
				remainder -= divider
			divider >>= 1
			bit >>= 1
		while bit and remainder:
			if (remainder >= divider):
				quotient |= bit    
				remainder -= divider
			remainder <<= 1
			bit >>= 1
		if (remainder >= divider):
			quotient+=1
		result = quotient
		if ((a ^ b) & 0x80000000):
			if (result == FIX16_MINIMUM):
				return FIX16_OVERFLOW
			result = -result
		return result
	
	def _fix16_sqrt(self,x):
		x=int(x)
		num=x&0xFFFFFFFF
		result = 0
		bit = 1 << 30
		while (bit > num):
			bit >>=2
		for n in range(0,2):
			while (bit):
				if (num >= result + bit):
					num = num-(result + bit)&0xFFFFFFFF
					result = (result >> 1) + bit
				else:
					result = (result >> 1)
				bit >>= 2
			if n==0:
				if num > 65535:
					num = (num -result)&0xFFFFFFFF
					num = ((num << 16) - 0x8000)&0xFFFFFFFF
					result = ((result << 16) + 0x8000)&0xFFFFFFFF
				else:
					num = ((num << 16)&0xFFFFFFFF)
					result =((result << 16)&0xFFFFFFFF)
				bit = 1 << 14
		if (num > result):
				result+=1
		return result
	
	def _fix16_exp(self,x):
		x=int(x)
		exp_pos_values=[self._f16(2.7182818), self._f16(1.1331485), self._f16(1.0157477), self._f16(1.0019550)]
		exp_neg_values=[self._f16(0.3678794), self._f16(0.8824969), self._f16(0.9844964), self._f16(0.9980488)]
		if (x >= self._f16(10.3972)):
			return FIX16_MAXIMUM
		if (x <= self._f16(-11.7835)):
			return 0
		if (x < 0):
			x = -x
			exp_values = exp_neg_values
		else:
			exp_values = exp_pos_values
		res = FIX16_ONE
		arg = FIX16_ONE
		for i in range(0,4):
			while (x >= arg):
				res = self._fix16_mul(res, exp_values[i])
				x -= arg
			arg >>=3
		return res
	
	def vocalgorithm_init(self):
		self.params.mvoc_index_offset = (self._f16(VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT))
		self.params.mtau_mean_variance_hours = self._f16(VOCALGORITHM_TAU_MEAN_VARIANCE_HOURS)
		self.params.mgating_max_duration_minutes =self._f16(VOCALGORITHM_GATING_MAX_DURATION_MINUTES)
		self.params.msraw_std_initial = self._f16(VOCALGORITHM_SRAW_STD_INITIAL)
		self.params.muptime = self._f16(0.)
		self.params.msraw = self._f16(0.)
		self.params.mvoc_index = 0
		self._vocalgorithm__init_instances()
	
	def _vocalgorithm__init_instances(self):
		self._vocalgorithm__mean_variance_estimator__init()
		self._vocalgorithm__mean_variance_estimator__set_parameters(self._f16(VOCALGORITHM_SRAW_STD_INITIAL), self.params.mtau_mean_variance_hours,self.params.mgating_max_duration_minutes)
		self._vocalgorithm__mox_model__init()
		self._vocalgorithm__mox_model__set_parameters(self._vocalgorithm__mean_variance_estimator__get_std(),self._vocalgorithm__mean_variance_estimator__get_mean())
		self._vocalgorithm__sigmoid_scaled__init()
		self._vocalgorithm__sigmoid_scaled__set_parameters(self.params.mvoc_index_offset)
		self._vocalgorithm__adaptive_lowpass__init()
		self._vocalgorithm__adaptive_lowpass__set_parameters()
	
	def _vocalgorithm_get_states(self):
		state0 = self._vocalgorithm__mean_variance_estimator__get_mean()
		state1 = _vocalgorithm__mean_variance_estimator__get_std()
		return state0, state1
	
	def _vocalgorithm_set_states(self,state0,state1):
		self._vocalgorithm__mean_variance_estimator__set_states( state0, state1, self._f16(VOCALGORITHM_PERSISTENCE_UPTIME_GAMMA))
		self.params.msraw = state0
	
	def _vocalgorithm_set_tuning_parameters(self, voc_index_offset, learning_time_hours, gating_max_duration_minutes, std_initial):
		self.params.mvoc_index_offset = self._fix16_from_int(voc_index_offset)
		self.params.mtau_mean_variance_hours = self._fix16_from_int(learning_time_hours)
		self.params.mgating_max_duration_minutes =self._fix16_from_int(gating_max_duration_minutes)
		self.params.msraw_std_initial = self._fix16_from_int(std_initial)
		self._vocalgorithm__init_instances()
	
	def vocalgorithm_process(self, sraw):
		if ((self.params.muptime <= self._f16(VOCALGORITHM_INITIAL_BLACKOUT))):
			self.params.muptime = self.params.muptime + self._f16(VOCALGORITHM_SAMPLING_INTERVAL)
		else:
			if (((sraw > 0) and (sraw < 65000))):
				if ((sraw < 20001)):
					sraw = 20001
				elif((sraw > 52767)):
					sraw = 52767
				self.params.msraw = self._fix16_from_int((sraw - 20000))
			self.params.mvoc_index =self._vocalgorithm__mox_model__process(self.params.msraw)
			self.params.mvoc_index =self._vocalgorithm__sigmoid_scaled__process(self.params.mvoc_index)
			self.params.mvoc_index =self._vocalgorithm__adaptive_lowpass__process(self.params.mvoc_index)
			if ((self.params.mvoc_index < self._f16(0.5))):
				self.params.mvoc_index = self._f16(0.5)
			if self.params.msraw > self._f16(0.):
				self._vocalgorithm__mean_variance_estimator__process(self.params.msraw, self.params.mvoc_index)
				self._vocalgorithm__mox_model__set_parameters(self._vocalgorithm__mean_variance_estimator__get_std(),self._vocalgorithm__mean_variance_estimator__get_mean())
		voc_index = self._fix16_cast_to_int((self.params.mvoc_index + self._f16(0.5))) 
		return voc_index
	
	def _vocalgorithm__mean_variance_estimator__init(self):
		self._vocalgorithm__mean_variance_estimator__set_parameters(self._f16(0.),self._f16(0.),self._f16(0.))
		self._vocalgorithm__mean_variance_estimator___init_instances()
	
	def _vocalgorithm__mean_variance_estimator___init_instances(self):
		self._vocalgorithm__mean_variance_estimator___sigmoid__init()
	
	def _vocalgorithm__mean_variance_estimator__set_parameters(self, std_initial, tau_mean_variance_hours, gating_max_duration_minutes):
		self.params.m_mean_variance_estimator_gating_max_duration_minutes = gating_max_duration_minutes
		self.params.m_mean_variance_estimator_initialized = 0
		self.params.m_mean_variance_estimator_mean = self._f16(0.)
		self.params.m_mean_variance_estimator_sraw_offset = self._f16(0.)
		self.params.m_mean_variance_estimator_std = std_initial
		self.params.m_mean_variance_estimator_gamma =self._fix16_div(self._f16((VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING *(VOCALGORITHM_SAMPLING_INTERVAL / 3600.))\
						                                                          ),(tau_mean_variance_hours +self._f16((VOCALGORITHM_SAMPLING_INTERVAL / 3600.))))
		self.params.m_mean_variance_estimator_gamma_initial_mean =self._f16(((VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING *VOCALGORITHM_SAMPLING_INTERVAL) \
						                                                        /(VOCALGORITHM_TAU_INITIAL_MEAN + VOCALGORITHM_SAMPLING_INTERVAL)))
		self.params.m_mean_variance_estimator_gamma_initial_variance = self._f16(((VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING *VOCALGORITHM_SAMPLING_INTERVAL) \
						                                                             /(VOCALGORITHM_TAU_INITIAL_VARIANCE + VOCALGORITHM_SAMPLING_INTERVAL)))
		self.params.m_mean_variance_estimator_gamma_mean = self._f16(0.)
		self.params.m_mean_variance_estimator__gamma_variance = self._f16(0.)
		self.params.m_mean_variance_estimator_uptime_gamma = self._f16(0.)
		self.params.m_mean_variance_estimator_uptime_gating = self._f16(0.)
		self.params.m_mean_variance_estimator_gating_duration_minutes = self._f16(0.)
	
	def _vocalgorithm__mean_variance_estimator__set_states(self, mean, std, uptime_gamma):
		self.params.m_mean_variance_estimator_mean = mean
		self.params.m_mean_variance_estimator_std = std
		self.params.m_mean_variance_estimator_uptime_gamma = uptime_gamma
		self.params.m_mean_variance_estimator_initialized = true
		
	
	def _vocalgorithm__mean_variance_estimator__get_std(self):
		return self.params.m_mean_variance_estimator_std
	
	def _vocalgorithm__mean_variance_estimator__get_mean(self):
		return (self.params.m_mean_variance_estimator_mean +self.params.m_mean_variance_estimator_sraw_offset)
	
	def _vocalgorithm__mean_variance_estimator___calculate_gamma(self, voc_index_from_prior):
		uptime_limit = self._f16((VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX -VOCALGORITHM_SAMPLING_INTERVAL))
		if self.params.m_mean_variance_estimator_uptime_gamma < uptime_limit:
			self.params.m_mean_variance_estimator_uptime_gamma =(self.params.m_mean_variance_estimator_uptime_gamma +self._f16(VOCALGORITHM_SAMPLING_INTERVAL))
		
		if self.params.m_mean_variance_estimator_uptime_gating < uptime_limit:
			self.params.m_mean_variance_estimator_uptime_gating =(self.params.m_mean_variance_estimator_uptime_gating +self._f16(VOCALGORITHM_SAMPLING_INTERVAL))
		
		self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self._f16(1.), self._f16(VOCALGORITHM_INITI_DURATION_MEAN),self._f16(VOCALGORITHM_INITI_TRANSITION_MEAN))
		sigmoid_gamma_mean =self._vocalgorithm__mean_variance_estimator___sigmoid__process(self.params.m_mean_variance_estimator_uptime_gamma)
		gamma_mean =(self.params.m_mean_variance_estimator_gamma +(self._fix16_mul((self.params.m_mean_variance_estimator_gamma_initial_mean -self.params.m_mean_variance_estimator_gamma),sigmoid_gamma_mean)))
		gating_threshold_mean =(self._f16(VOCALGORITHM_GATING_THRESHOLD)\
						        +(self._fix16_mul(self._f16((VOCALGORITHM_GATING_THRESHOLD_INITIAL -VOCALGORITHM_GATING_THRESHOLD)),\
						         self._vocalgorithm__mean_variance_estimator___sigmoid__process(self.params.m_mean_variance_estimator_uptime_gating))))
		self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self._f16(1.),gating_threshold_mean,self._f16(VOCALGORITHM_GATING_THRESHOLD_TRANSITION))
		
		sigmoid_gating_mean =self._vocalgorithm__mean_variance_estimator___sigmoid__process(voc_index_from_prior)
		self.params.m_mean_variance_estimator_gamma_mean =(self._fix16_mul(sigmoid_gating_mean, gamma_mean))
		
		self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self._f16(1.), self._f16(VOCALGORITHM_INITI_DURATION_VARIANCE),self._f16(VOCALGORITHM_INITI_TRANSITION_VARIANCE))
		
		sigmoid_gamma_variance =self._vocalgorithm__mean_variance_estimator___sigmoid__process( self.params.m_mean_variance_estimator_uptime_gamma)
		
		gamma_variance =(self.params.m_mean_variance_estimator_gamma +\
						(self._fix16_mul((self.params.m_mean_variance_estimator_gamma_initial_variance \
						                  -self.params.m_mean_variance_estimator_gamma),\
						                  (sigmoid_gamma_variance - sigmoid_gamma_mean))))
		
		gating_threshold_variance =(self._f16(VOCALGORITHM_GATING_THRESHOLD) \
						            +(self._fix16_mul(self._f16((VOCALGORITHM_GATING_THRESHOLD_INITIAL -VOCALGORITHM_GATING_THRESHOLD)),\
						             self._vocalgorithm__mean_variance_estimator___sigmoid__process( self.params.m_mean_variance_estimator_uptime_gating))))
		
		self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self._f16(1.), gating_threshold_variance,self._f16(VOCALGORITHM_GATING_THRESHOLD_TRANSITION))
		
		sigmoid_gating_variance =self._vocalgorithm__mean_variance_estimator___sigmoid__process( voc_index_from_prior)
		
		self.params.m_mean_variance_estimator__gamma_variance =(self._fix16_mul(sigmoid_gating_variance, gamma_variance))
		
		self.params.m_mean_variance_estimator_gating_duration_minutes =(self.params.m_mean_variance_estimator_gating_duration_minutes \
						                                                  +(self._fix16_mul(self._f16((VOCALGORITHM_SAMPLING_INTERVAL / 60.)),\
						                                                                   ((self._fix16_mul((self._f16(1.) - sigmoid_gating_mean),\
						                                                                                     self._f16((1. + VOCALGORITHM_GATING_MAX_RATIO))))\
						                                                                      -self._f16(VOCALGORITHM_GATING_MAX_RATIO)))))
		
		if ((self.params.m_mean_variance_estimator_gating_duration_minutes <self._f16(0.))):
			self.params.m_mean_variance_estimator_gating_duration_minutes = self._f16(0.)
		
		if ((self.params.m_mean_variance_estimator_gating_duration_minutes >self.params.m_mean_variance_estimator_gating_max_duration_minutes)):
			self.params.m_mean_variance_estimator_uptime_gating = self._f16(0.)
	
	def _vocalgorithm__mean_variance_estimator__process(self, sraw, voc_index_from_prior):
		if ((self.params.m_mean_variance_estimator_initialized == 0)):
			self.params.m_mean_variance_estimator_initialized = 1
			self.params.m_mean_variance_estimator_sraw_offset = sraw
			self.params.m_mean_variance_estimator_mean = self._f16(0.)
		else:
			if (((self.params.m_mean_variance_estimator_mean >= self._f16(100.)) or (self.params.m_mean_variance_estimator_mean <= self._f16(-100.)))):
				self.params.m_mean_variance_estimator_sraw_offset =(self.params.m_mean_variance_estimator_sraw_offset +self.params.m_mean_variance_estimator_mean)
				self.params.m_mean_variance_estimator_mean = self._f16(0.)
			
			sraw = (sraw - self.params.m_mean_variance_estimator_sraw_offset)
			self._vocalgorithm__mean_variance_estimator___calculate_gamma( voc_index_from_prior)
			delta_sgp = (self._fix16_div((sraw - self.params.m_mean_variance_estimator_mean),self._f16(VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING)))
			if ((delta_sgp < self._f16(0.))):
				c = (self.params.m_mean_variance_estimator_std - delta_sgp)
			else:
				c = (self.params.m_mean_variance_estimator_std + delta_sgp)
			additional_scaling = self._f16(1.)
			if ((c > self._f16(1440.))):
				additional_scaling = self._f16(4.)
			self.params.m_mean_variance_estimator_std = self._fix16_mul(self._fix16_sqrt((self._fix16_mul(additional_scaling,\
						                                                                  (self._f16(VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING) -self.params.m_mean_variance_estimator__gamma_variance)))),\
						                                                  self._fix16_sqrt(((self._fix16_mul(self.params.m_mean_variance_estimator_std,\
						                                                                                    (self._fix16_div(self.params.m_mean_variance_estimator_std,\
						                                                                                    (self._fix16_mul(self._f16(VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING),additional_scaling)))))) \
						                                                                  +(self._fix16_mul((self._fix16_div((self._fix16_mul(self.params.m_mean_variance_estimator__gamma_variance,delta_sgp)),additional_scaling))\
						                                                                  ,delta_sgp)))))
			self.params.m_mean_variance_estimator_mean =(self.params.m_mean_variance_estimator_mean +(self._fix16_mul(self.params.m_mean_variance_estimator_gamma_mean,delta_sgp)))
	
	def _vocalgorithm__mean_variance_estimator___sigmoid__init(self):
		self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self._f16(0.), self._f16(0.), self._f16(0.))
	
	def _vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self, L, X0, K):
		self.params.m_mean_variance_estimator_sigmoid_l = L
		self.params.m_mean_variance_estimator_sigmoid_k = K
		self.params.m_mean_variance_estimator_sigmoid_x0 = X0
	
	def _vocalgorithm__mean_variance_estimator___sigmoid__process(self, sample):
		x = (self._fix16_mul(self.params.m_mean_variance_estimator_sigmoid_k,(sample - self.params.m_mean_variance_estimator_sigmoid_x0)))
		if ((x < self._f16(-50.))):
			return self.params.m_mean_variance_estimator_sigmoid_l
		elif ((x > self._f16(50.))):
			return self._f16(0.)
		else:
			return (self._fix16_div(self.params.m_mean_variance_estimator_sigmoid_l,(self._f16(1.) + self._fix16_exp(x))))
	
	def _vocalgorithm__mox_model__init(self):
		self._vocalgorithm__mox_model__set_parameters(self._f16(1.),self._f16(0.))
	
	def _vocalgorithm__mox_model__set_parameters(self,SRAW_STD,SRAW_MEAN):
		self.params.m_mox_model_sraw_std = SRAW_STD
		self.params.m_mox_model_sraw_mean = SRAW_MEAN
	
	def _vocalgorithm__mox_model__process(self,sraw):
		return (self._fix16_mul((self._fix16_div((sraw - self.params.m_mox_model_sraw_mean),(-(self.params.m_mox_model_sraw_std +self._f16(VOCALGORITHM_SRAW_STD_BONUS))))),self._f16(VOCALGORITHM_VOC_INDEX_GAIN)))
	
	def _vocalgorithm__sigmoid_scaled__init(self):
		self._vocalgorithm__sigmoid_scaled__set_parameters(self._f16(0.))
	
	def _vocalgorithm__sigmoid_scaled__set_parameters(self,offset):
		self.params.m_sigmoid_scaled_offset = offset
	
	def _vocalgorithm__sigmoid_scaled__process(self,sample):
		x = (self._fix16_mul(self._f16(VOCALGORITHM_SIGMOID_K),(sample - self._f16(VOCALGORITHM_SIGMOID_X0))))
		if ((x < self._f16(-50.))):
			return self._f16(VOCALGORITHM_SIGMOID_L)
		elif ((x > self._f16(50.))):
			return self._f16(0.)
		else:
			if ((sample >= self._f16(0.))):
				shift = (self._fix16_div((self._f16(VOCALGORITHM_SIGMOID_L) -(self._fix16_mul(self._f16(5.), self.params.m_sigmoid_scaled_offset))),self._f16(4.)))
				return ((self._fix16_div((self._f16(VOCALGORITHM_SIGMOID_L) + shift),(self._f16(1.) + self._fix16_exp(x)))) -shift)
			else:
				return (self._fix16_mul((self._fix16_div(self.params.m_sigmoid_scaled_offset,self._f16(VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT))),\
						                 (self._fix16_div(self._f16(VOCALGORITHM_SIGMOID_L),(self._f16(1.) + self._fix16_exp(x))))))
	
	def _vocalgorithm__adaptive_lowpass__init(self):
		self._vocalgorithm__adaptive_lowpass__set_parameters()
	
	def _vocalgorithm__adaptive_lowpass__set_parameters(self):
		self.params.m_adaptive_lowpass_a1 =self._f16((VOCALGORITHM_SAMPLING_INTERVAL /(VOCALGORITHM_LP_TAU_FAST + VOCALGORITHM_SAMPLING_INTERVAL)))
		self.params.m_adaptive_lowpass_a2 =self._f16((VOCALGORITHM_SAMPLING_INTERVAL /(VOCALGORITHM_LP_TAU_SLOW + VOCALGORITHM_SAMPLING_INTERVAL)))
		self.params.m_adaptive_lowpass_initialized = 0
	
	def _vocalgorithm__adaptive_lowpass__process(self,sample):
		if ((self.params.m_adaptive_lowpass_initialized == 0)):
			self.params.m_adaptive_lowpass_x1 = sample
			self.params.m_adaptive_lowpass_x2 = sample
			self.params.m_adaptive_lowpass_x3 = sample
			self.params.m_adaptive_lowpass_initialized = 1
		self.params.m_adaptive_lowpass_x1 =((self._fix16_mul((self._f16(1.) - self.params.m_adaptive_lowpass_a1),self.params.m_adaptive_lowpass_x1)) +(self._fix16_mul(self.params.m_adaptive_lowpass_a1, sample)))
		
		self.params.m_adaptive_lowpass_x2 =((self._fix16_mul((self._f16(1.) - self.params.m_adaptive_lowpass_a2),self.params.m_adaptive_lowpass_x2)) +(self._fix16_mul(self.params.m_adaptive_lowpass_a2, sample)))
		
		abs_delta =(self.params.m_adaptive_lowpass_x1 - self.params.m_adaptive_lowpass_x2)
		
		if ((abs_delta < self._f16(0.))):
			abs_delta = (-abs_delta)
		F1 = self._fix16_exp((self._fix16_mul(self._f16(VOCALGORITHM_LP_ALPHA), abs_delta)))
		tau_a =((self._fix16_mul(self._f16((VOCALGORITHM_LP_TAU_SLOW - VOCALGORITHM_LP_TAU_FAST)),F1)) +self._f16(VOCALGORITHM_LP_TAU_FAST))
		a3 = (self._fix16_div(self._f16(VOCALGORITHM_SAMPLING_INTERVAL),(self._f16(VOCALGORITHM_SAMPLING_INTERVAL) + tau_a)))
		self.params.m_adaptive_lowpass_x3 =((self._fix16_mul((self._f16(1.) - a3), self.params.m_adaptive_lowpass_x3)) +(self._fix16_mul(a3, sample)))
		return self.params.m_adaptive_lowpass_x3
		
## copied from https://github.com/DFRobot/DFRobot_BMP388/blob/master/raspbarry/example/I2CReadTemperature/I2CReadTemperature.py
## with some simplification ie i2c setup
""" 
  @file DFRobot_SGP40.py
  @note DFRobot_SGP40 Class infrastructure, implementation of underlying methods
  @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @licence     The MIT License (MIT)
  @author      [yangfeng]<feng.yang@dfrobot.com> 
  version  V1.0
  date  2021-01-15
  @get from https://www.dfrobot.com
  @url https://github.com/DFRobot/DFRobot_SGP40
"""


class DFRobot_SGP40:
	DFRobot_SGP40_ICC_ADDR                           = 0x59
	TEST_OK_H                                        = 0xD4
	TEST_OK_L                                        = 0x00
	CMD_HEATER_OFF_H                                 = 0x36
	CMD_HEATER_OFF_L                                 = 0x15
			                                         
	CMD_MEASURE_TEST_H                               = 0x28
	CMD_MEASURE_TEST_L                               = 0x0E
			                                         
	CMD_SOFT__reset_H                                = 0x00
	CMD_SOFT__reset_L                                = 0x06
			                                         
	CMD_MEASURE_RAW_H                                = 0x26
	CMD_MEASURE_RAW_L                                = 0x0F

	DURATION_READ_RAW_VOC                            = 0.03
	DURATION_WAIT_MEASURE_TEST                       = 0.25
	OFFSET                                           = 0x00
		
	def __init__(self,bus = 1,relative_humidity = 50,temperature_c = 25):
		""" Module init
		
		:param bus:int Set to IICBus
		:param relative_humidity:float Set to relative_humidity
		:param temperature_c:float Set to temperature
		"""
		self.__i2cbus = smbus.SMBus(bus)
		self.__my_vocalgorithm = DFRobot_VOCAlgorithm()
		self.__i2c_addr = self.DFRobot_SGP40_ICC_ADDR
		self.__temperature_c = temperature_c
		self.__relative_humidity = relative_humidity
		self.__rh = 0
		self.__temc = 0
		self.__rh_h = 0
		self.__rh_l = 0
		self.__temc_h = 0
		self.__temc_l = 0
		self.__temc__crc = 0
		self.__rh__crc = 0
		
	def set_envparams(self, relative_humidity,temperature_c):
		""" Set temperature and humidity
		
		:param relative_humidity:float Set to relative_humidity
		:param temperature_c:float Set to temperature
		"""
		self.__temperature_c = temperature_c
		self.__relative_humidity = relative_humidity
		
	def begin(self,duration = 10):
		""" start equipment
		
		:param duration:int Set to Warm-up time
		:return int equipment condition
		  : 0 succeed
		  : 1 failed 
		"""
		self.__my_vocalgorithm.vocalgorithm_init()
		timeOne = int(time.time())
		while(int(time.time())-timeOne<duration):
			self.get_voc_index()
		return self.__measure_test()
		
	def measure_raw(self):
		""" Get raw data
		
		: return int collect result
		  :-1 collect failed
		  :>0 the collection value
		"""
		self.__data_transform()
		self.__i2cbus.write_i2c_block_data(self.__i2c_addr,self.CMD_MEASURE_RAW_H, [self.CMD_MEASURE_RAW_L,self.__rh_h,self.__rh_l,self.__rh__crc,self.__temc_h,self.__temc_l,self.__temc__crc])
		time.sleep(self.DURATION_READ_RAW_VOC)
		raw = self.__i2cbus.read_i2c_block_data(self.__i2c_addr,self.OFFSET,3)
		if self.__check__crc(raw) == 0:
			return raw[0]<<8 | raw[1]
		else:
			return -1
		
	def get_voc_index(self):
		""" Measure VOC index after humidity compensation
		:note  VOC index can indicate the quality of the air directly. The larger the value, the worse the air quality.
		:note    0-100,no need to ventilate, purify
		:note    100-200,no need to ventilate, purify
		:note    200-400,ventilate, purify
		:note    00-500,ventilate, purify intensely
		:return int The VOC index measured, ranged from 0 to 500
		"""
		raw = self.measure_raw()
		if raw<0:
			return -1
		else:
			vocIndex = self.__my_vocalgorithm.vocalgorithm_process(raw)
			return vocIndex
		  
	def __data_transform(self):
		""" Convert environment parameters

		"""
		self.__rh = int(((self.__relative_humidity*65535)/100+0.5))
		self.__temc = int(((self.__temperature_c+45)*(65535/175)+0.5))
		self.__rh_h = int(self.__rh)>>8
		self.__rh_l = int(self.__rh)&0xFF
		self.__rh__crc = self.__crc(self.__rh_h,self.__rh_l)
		self.__temc_h = int(self.__temc)>>8
		self.__temc_l = int(self.__temc)&0xFF
		self.__temc__crc = self.__crc(self.__temc_h,self.__temc_l) 
		
	def __measure_test(self):
		""" Sensor self-test
		
		:return int self-test condition
		  : 0 succeed
		  : 1 failed 
		"""
		self.__i2cbus.write_i2c_block_data(self.__i2c_addr,self.CMD_MEASURE_TEST_H, [self.CMD_MEASURE_TEST_L])
		time.sleep(self.DURATION_WAIT_MEASURE_TEST)
		raw = self.__i2cbus.read_i2c_block_data(self.__i2c_addr,self.OFFSET,2)
		if raw[0] == self.TEST_OK_H and raw[1] == self.TEST_OK_L :
			return 0
		else:
			return 1
			
	def __reset(self):
		""" Sensor reset
		
		"""
		self.__i2cbus.write_i2c_block_data(self.__i2c_addr,self.CMD_SOFT__reset_H, [self.CMD_SOFT__reset_L])
	
	def __heater_off(self):
		""" spg40 Heater Off. Turn the hotplate off and stop the measurement. Subsequently, the sensor enters the idle mode.
		
		"""
		self.__i2cbus.write_i2c_block_data(self.__i2c_addr,self.CMD_HEATER_OFF_H, [self.CMD_HEATER_OFF_L])

	def __check__crc(self, raw):
		""" Verify the calibration value of the sensor
		
		:param raw : list Parameter to check
		:return int Check result
		  :-1 Check failed
		  : 0 Check succeed
		"""
		assert (len(raw) == 3)
		if self.__crc(raw[0], raw[1]) != raw[2]:
			return -1
		return 0

	def __crc(self,data_1,data_2):
		""" CRC
		
		:param  data1  High 8 bits data
		:param  data2  LOW 8 bits data
		:return int Calibration value
		"""
		crc = 0xff
		list = [data_1,data_2]
		for i in range(0,2):
			crc = crc^list[i]
			for bit in range(0,8):
				if(crc&0x80):
					crc = ((crc <<1)^0x31)
				else:
					crc = (crc<<1)
			crc = crc&0xFF
		return crc
# ===========================================================================
# read params
# ===========================================================================

###############################
def readParams():
	global sensorList, sensors, logDir, sensor, sensorRefreshSecs
	global rawOld
	global deltaX, minSendDelta
	global oldRaw, lastRead
	global lastMeasurement, sendToIndigoSecs
	try:



		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		
		externalSensor = False
		sensorList = []
		sensorsOld = copy.copy(sensors)

	
		U.getGlobalParams(inp)
		  
		if "sensorList"			in inp:	 sensorList=			 (inp["sensorList"])
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		
 
		if sensor not in sensors:
			U.logger.log(30, "{} is not in parameters = not enabled, stopping {}.py".format(G.program,G.program) )
			exit()
			

		U.logger.log(10, "{} reading new parameter file".format(G.program) )

		deltaX={}
		restart = False
		sendToIndigoSecs = G.sendToIndigoSecs	
		for devId in sensors[sensor]:

			sendToIndigoSecs = G.sendToIndigoSecs	  
			try:
				if "sendToIndigoSecs" in sensors[sensor][devId]:
					sendToIndigoSecs = float(sensors[sensor][devId]["sendToIndigoSecs"])
			except: pass

			sensorRefreshSecs = 5  
			try:
				if "sensorRefreshSecs" in sensors[sensor][devId]:
					sensorRefreshSecs = float(sensors[sensor][devId]["sensorRefreshSecs"])
			except: pass


			deltaX[devId] = 0.1
			try:
				if devId not in deltaX: deltaX[devId]  = 0.1
				if "deltaX" in sensors[sensor][devId]: 
					deltaX[devId]= float(sensors[sensor][devId]["deltaX"])/100.
			except: pass

			minSendDelta = 5.
			try:
				if "minSendDelta" in sensors[sensor][devId]: 
					minSendDelta = float(sensors[sensor][devId]["minSendDelta"])
			except: pass

				
			if devId not in SENSOR or  restart:
				U.logger.log(20," new parameters read: minSendDelta:{};  deltaX:{}; sensorRefreshSecs:{}".format(minSendDelta, deltaX[devId], sensorRefreshSecs) )
				startSensor(devId)
				if SENSOR[devId] == "":
					return
				
		deldevID={}		   
		for devId in SENSOR:
			if devId not in sensors[sensor]:
				deldevID[devId] = 1
		for dd in  deldevID:
			del SENSOR[dd]
		if len(SENSOR) == 0: 
			####exit()
			pass

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "{}".format(sensors[sensor]))
		



#################################
def startSensor(devId):
	global sensors, sensor
	global SENSOR

	
	try:
		xx = SENSOR[devId] 
	except:
		try:
			time.sleep(1)
			SENSOR[devId]  = DFRobot_SGP40(bus = 1,relative_humidity = 50,temperature_c = 25)
			SENSOR[devId].begin(10)
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			SENSOR[devId] = ""
			return



#################################
def getValues(devId):
	global sensor, sensors,	 SENSOR, badSensor
	global lastMeasurement, sendToIndigoSecs

	try:
		if SENSOR[devId] == "": 
			badSensor += 1
			return "badSensor"

		raw   		 = 0
		vocIndex  	 = 0

		raw			= SENSOR[devId].measure_raw()
		VOC			= SENSOR[devId].get_voc_index()
		badSensor = 0
		data = {"raw":	 raw, 
				"VOC": VOC
				}
		return data
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	badSensor += 1
	if badSensor > 3: return "badSensor"
	return ""





############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, SENSOR, minSendDelta
global oldRaw, lastRead

sendToIndigoSecs			= 80
lastMeasurement				= time.time()
oldRaw						= ""
lastRead					= 0
minSendDelta				= 5.
loopCount					= 0
sensorRefreshSecs			= -1
NSleep						= 100
sensorList					= []
sensors						= {}
sensor						= G.program
quick						= False
display						= "0"
output						= {}
badSensor					= 0
sensorActive				= False
rawOld						= ""
SENSOR				= {}
deltaX				  		= {}
myPID		= str(os.getpid())
U.setLogging()
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)




lastValues0			= {"raw":0,"VOC":0}
lastValues			= {}
lastValues2			= {}
lastData			= {}
lastSend			= 0
lastDisplay			= 0
startTime			= time.time()
G.lastAliveSend		= time.time() -1000

lastMeasurement 	= time.time() -5

sensorWasBad 		= False
while True:
	try:
		tt = time.time()
		sendData = False
		data ={}
		if sensor in sensors:
			data = {"sensors": {sensor:{}}}
			for devId in sensors[sensor]:
				if devId not in lastValues: 
					lastValues[devId]  =copy.copy(lastValues0)
					lastValues2[devId] =copy.copy(lastValues0)
				values = getValues(devId)
				if values == "": 
					continue

				data["sensors"][sensor][devId]={}
				if values == "badSensor":
					sensorWasBad = True
					data["sensors"][sensor][devId]="badSensor"
					if badSensor < 5: 
						U.logger.log(30," bad sensor")
						U.sendURL(data)
					else:
						U.restartMyself(param="", reason="badsensor",doPrint=True)
					lastValues2[devId] =copy.copy(lastValues0)
					lastValues[devId]  =copy.copy(lastValues0)
					continue
				elif values["raw"] !="":
					if sensorWasBad: # sensor was bad, back up again, need to do a restart to set config 
						U.restartMyself(reason=" back from bad sensor, need to restart to get sensors reset",doPrint=False)
					
					data["sensors"][sensor][devId] = values
					deltaN =0
					for xx in lastValues0:
						try:
							current = float(values[xx])
							delta	= current-lastValues2[devId][xx]
							delta  /=  max (0.5,(current+lastValues2[devId][xx])/2.)
							deltaN	= abs(deltaN )
							lastValues[devId][xx] = current
						except: pass
				else:
					continue
				if (   ( deltaN > deltaX[devId]	 ) or  (  tt - abs(sendToIndigoSecs) > G.lastAliveSend  ) or	quick	) and  ( tt - G.lastAliveSend > minSendDelta ):
							sendData = True
							lastValues2[devId] = copy.copy(lastValues[devId])
		if sendData:
			U.sendURL(data)
		U.makeDATfile(G.program, data)

		loopCount +=1

		##U.makeDATfile(G.program, data)
		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		time.sleep( max(5, (lastMeasurement+sensorRefreshSecs) - time.time() ) )
		lastMeasurement = time.time()

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
sys.exit(0)
		
