#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for decision tree
# objective: To cluster different service
# JialongLi 2017/03/18

import re
import os
import sys
import pickle
import copy
import random

USER_NUM = 1000
reload(sys)
sys.setdefaultencoding( "utf-8" )
from sklearn import tree
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans

# 0 represent Sunday, 1: Monday, 6: Saturday
day_index = {'0507': 1, '0508': 2, '0509': 3, '0510': 4, '0511': 5, '0512': 6, '0513': 0, 
			 '0604': 1, '0605': 2, '0606': 3, '0607': 4, '0608': 5, '0609': 6, '0610': 0, 
			 '0702': 1, '0703': 2, '0704': 3, '0705': 4, '0706': 5, '0707': 6, '0708': 0, 
			 '0806': 1, '0807': 2, '0808': 3, '0809': 4, '0810': 5, '0811': 6, '0812': 0}

service_type = ['idle', 'off', 'W', 'G', 'S', 'V']

# get activity_dict
# user's activity: default value is 'off'
# format: {id_1:{'0507': [24/PERIOD], '0508': ['idle', 'W', 'G']}, id_2}
def get_activity_dict(activity_dict_path):
	pkl_file = open(activity_dict_path, 'rb')
	activity_dict = pickle.load(pkl_file)
	pkl_file.close()
	return activity_dict

# data are divided into train data and test data
# first three weeks: train data; last week: test data
# train_dict and test_dict are subset of activity_dict
# format: {id_1:{'0507': [24/PERIOD], '0508': ['idle', 'W', 'G']}, id_2}
def data_segement(activity_dict, train_dict_path, test_dict_path):
	train_dict = {}
	test_dict = {}
	for key_0, value_0 in activity_dict.items(): # key_0: user_id
		train_dict[key_0] = {}
		test_dict[key_0] = {}
		for key, value in value_0.items():
			if key[1] == '8':         # data of August, test set
				test_dict[key_0][key] = value
			else:
				train_dict[key_0][key] = value  # train set

	output_1 = open(train_dict_path, 'wb')
	pickle.dump(train_dict, output_1)
	output_2 = open(test_dict_path, 'wb')
	pickle.dump(test_dict, output_2)
	output_1.close()
	output_2.close()

# get train data and test data
def get_data(train_dict_path, test_dict_path):
	pkl_file_1 = open(train_dict_path, 'rb')
	pkl_file_2 = open(test_dict_path, 'rb')
	train_dict = pickle.load(pkl_file_1)
	test_dict = pickle.load(pkl_file_2)
	pkl_file_1.close()
	pkl_file_2.close()
	return train_dict, test_dict

# get profile
def get_profile(profile_path):
	pkl_file = open(profile_path, 'rb')
	profile = pickle.load(pkl_file)
	return profile

# select different features
# feature format: [user_id, gender, age, edu, job, hour, date], 7 features
# profile: dict, {user_id: [gender, age, edu, job]}
def feature_select(data_dict, profile, over_sampling):
	feature = []
	cate = []
	sampling_num = 20
	user_count = 0  # convert user_id to integer
	for user_id, all_dates in data_dict.items(): 
		one_user_profile = copy.deepcopy(profile[user_id])  # gender, age, edu, job
		one_user_profile.insert(0, user_count)        # insert user_id
		for date, activity in all_dates.items():
			for i in range(len(activity)):
				if 1:    #activity[i] != 'off':  # do not add 'off'
					sample = copy.deepcopy(one_user_profile)
					#del(sample[1:4])
					sample.append(int(i/6))  #(int(i/6))        # i represents hour
					sample.append(day_index[date])  # day_index: 7 days in one week
					feature.append(sample)
					cate.append(activity[i])
					if over_sampling and len(sample) > 5:  # make sure that features are completed
						if activity[i] != 'off':
							sample_over = [[] for k in range(sampling_num)]
							for j in range(sampling_num):
								sample_over[j] = copy.deepcopy(sample)
								sample_over[j][-3] = random.randint(0, 8)  # random disturbance in job feature
								feature.append(sample_over[j])
								cate.append(activity[i])
		user_count += 1

	return feature, cate

# build features, all features
def feature_build(train_dict, test_dict, profile):
	feature_train, cate_train = feature_select(train_dict, profile, True)
	feature_test, cate_test = feature_select(test_dict, profile, False)
	return feature_train, feature_test, cate_train, cate_test

# calculating the hit rate
def cal_hit_rate(cate_predict, cate_test):
	hit_count = 0
	sample_test_count = len(cate_predict)
	for i in range(sample_test_count):
		if cate_predict[i] == cate_test[i]:
			hit_count += 1
	hit_rate = float(hit_count) / float(sample_test_count)
	return hit_rate

# calculating F value
def calculating_F_value(cate_predict, cate_test):
	n_predict = 0
	n_origin = 0
	hit_count = 0
	for item in cate_predict:
		if item != 'off':
			n_predict += 1
	for item in cate_test:
		if item != 'off':
			n_origin += 1
	for i in range(len(cate_predict)):
		if cate_predict[i] != 'off' and cate_predict[i] == cate_test[i]:
			hit_count += 1
	precision = float(hit_count) / float(n_predict)
	recall = float(hit_count) / float(n_origin)
	F_value = 2 * precision * recall / (precision + recall)
	print 'n_predict: ' + str(n_predict)
	print 'n_origin: ' + str(n_origin)
	print 'precision: ' + str(round(precision, 3))
	print 'recall: ' + str(round(recall, 3))
	print 'F_value: ' + str(round(F_value, 3))


# Attention: When you use this method, make sure that only 2 features are selected!! [user_id, hour]
# 1. select the service type using most in that period in past days
# 2. if user did not use service in that period before, select the service type using most in past days
# 3. if user did not use service before, select service randomly 
# service_count_hour: key = (user_id, hour, service_type) value = count
# service_count_past: key = (user_id, service_type)  value = count
# service_hour: key = (user_id, hour), value = [service_type, count]
# service_past: key = user_id, value = [service_type, count]
def conventional_method(feature_train, feature_test, cate_train):
	service_count_hour = {}
	service_count_past = {}
	for i in range(len(feature_train)):
		key_hour = (feature_train[i][0], feature_train[i][1], cate_train[i])
		if key_hour not in service_count_hour:
			service_count_hour[key_hour] = 1
		else:
			service_count_hour[key_hour] += 1

		key_past = (feature_train[i][0], cate_train[i])
		if key_past not in service_count_past:
			service_count_past[key_past] = 1
		else:
			service_count_past[key_past] += 1

	service_hour = {}
	service_past = {}
	for key, value in service_count_hour.items():
		key_hour = (key[0], key[1])
		if key_hour not in service_hour:
			service_hour[key_hour] = [key[2], value]
		else:
			if value > service_hour[key_hour][1]:
				service_hour[key_hour] = [key[2], value]
			else:
				pass

	for key, value in service_count_past.items():
		key_past = key[0]
		if key_past not in service_past:
			service_past[key_past] = [key[1], value]
		else:
			if value > service_past[key_past][1]:
				service_past[key_past] = [key[1], value]
			else:
				pass

	cate_predict = []
	for i in range(len(feature_test)):
		key_0 = (feature_test[i][0], feature_test[i][1])
		key_1 = feature_test[i][0]
		if key_0 in service_hour:
			value_0 = service_hour[key_0]
			cate_predict.append(value_0[0])
		elif key_1 in service_past:
			value_1 = service_past[key_1]
			cate_predict.append(value_1[0])
		else:
			random_num = random.randint(0, len(service_type)-1)
			cate_predict.append(service_type[random_num])

	return cate_predict

# decision tree
def decision_tree(feature_train, feature_test, cate_train):
	clf = tree.DecisionTreeClassifier()
	clf = clf.fit(feature_train, cate_train)
	cate_predict = clf.predict(feature_test)
	return cate_predict

# save cate_predict as pkl file for migration.py
def cate_predict_save(cate_predict, cate_predict_path):
	output = open(cate_predict_path, 'wb')
	pickle.dump(cate_predict, output)
	output.close()

if __name__ == '__main__':
	'''
	activity_dict_path = '../data/activity_dict.pkl'
	activity_dict = get_activity_dict(activity_dict_path)
	train_dict_path = '../data/train_dict.pkl'
	test_dict_path = '../data/test_dict.pkl'
	data_segement(activity_dict, train_dict_path, test_dict_path)
	'''
	
	train_dict_path = '../data/train_dict.pkl'
	test_dict_path = '../data/test_dict.pkl'
	train_dict, test_dict = get_data(train_dict_path, test_dict_path)

	profile_path = '../data/profile.pkl'
	profile = get_profile(profile_path)

	feature_train, feature_test, cate_train, cate_test = feature_build(train_dict, test_dict, profile)

	# decision tree
	cate_predict = decision_tree(feature_train, feature_test, cate_train)

	# conventional method
	#cate_predict = conventional_method(feature_train, feature_test, cate_train)

	
	hit_rate = cal_hit_rate(cate_predict, cate_test)
	hit_rate = 100.0 * round(hit_rate, 4)
	print "hit_rate:" + '\t' + str(hit_rate) + '%'
	print 'feature_train sample: ' + str(feature_train[1000])
	print 'feature_test sample: ' + str(feature_test[1000])

	calculating_F_value(cate_predict, cate_test)

	cate_predict_path = '../data/cate_predict.pkl'
	cate_predict_save(cate_predict, cate_predict_path)

	for item in feature_test:
		print item