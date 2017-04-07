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

# 0 represent Sunday, 1: Monday, 6: Saturday, 0: Sunday
day_index = {'0507': 1, '0508': 2, '0509': 3, '0510': 4, '0511': 5, '0512': 6, '0513': 0, 
			 '0604': 1, '0605': 2, '0606': 3, '0607': 4, '0608': 5, '0609': 6, '0610': 0, 
			 '0702': 1, '0703': 2, '0704': 3, '0705': 4, '0706': 5, '0707': 6, '0708': 0, 
			 '0806': 1, '0807': 2, '0808': 3, '0809': 4, '0810': 5, '0811': 6, '0812': 0}

service_type = ['I', 'F', 'W', 'G', 'S', 'V']

# get activity_dict
# user's activity: default value is 'F'
# format: {id_1:{'0507': [24/PERIOD], '0508': ['I', 'W', 'G']}, id_2}
def get_activity_dict(activity_dict_path):
	pkl_file = open(activity_dict_path, 'rb')
	activity_dict = pickle.load(pkl_file)
	pkl_file.close()
	return activity_dict

# data are divided into train data and test data
# first three weeks: train data; last week: test data
# train_dict and test_dict are subset of activity_dict, id format is different
# activity_dict format: {real id_1:{'0507': [24/PERIOD], '0508': ['I', 'W', 'G']}, id_2}
# user_id_index:  key = number, value = real id
def data_segement(activity_dict, train_dict_path, test_dict_path, user_id_index_path):
	train_dict = {}
	test_dict = {}
	user_count = 0
	user_id_index = {}
	for key_0, value_0 in activity_dict.items(): # key_0: real user_id
		train_dict[user_count] = {}
		test_dict[user_count] = {}
		user_id_index[user_count] = key_0
		for key, value in value_0.items():
			if key[1] == '8':         # data of August, test set
				test_dict[user_count][key] = value
			else:
				train_dict[user_count][key] = value  # train set
		user_count += 1

	output_1 = open(train_dict_path, 'wb')
	pickle.dump(train_dict, output_1)
	output_2 = open(test_dict_path, 'wb')
	pickle.dump(test_dict, output_2)
	output_3 = open(user_id_index_path, 'wb')
	pickle.dump(user_id_index, output_3)
	output_1.close()
	output_2.close()
	output_3.close()

# get train data and test data
# train_dict, test_dict format: {number id_1:{'0507': [24/PERIOD], '0508': ['I', 'W', 'G']}, id_2}
def get_data(train_dict_path, test_dict_path, user_id_index_path):
	pkl_file_1 = open(train_dict_path, 'rb')
	pkl_file_2 = open(test_dict_path, 'rb')
	pkl_file_3 = open(user_id_index_path, 'rb')
	train_dict = pickle.load(pkl_file_1)
	test_dict = pickle.load(pkl_file_2)
	user_id_index = pickle.load(pkl_file_3)
	pkl_file_1.close()
	pkl_file_2.close()
	pkl_file_3.close()
	return train_dict, test_dict, user_id_index

# get profile
def get_profile(profile_path):
	pkl_file = open(profile_path, 'rb')
	profile = pickle.load(pkl_file)
	return profile

# select different features
# feature format: [user_id, gender, age, edu, job, hour, date], 7 features
# profile: dict, {real user_id: [gender, age, edu, job]}
# feature format: double list, outer list element is a sample: [number user_id, gender, age, edu, job, hour, date]
# category format: list, element is service type, length = feature
def feature_select(data_dict, profile, user_id_index, is_over_sampling):
	feature = []
	category = []
	over_sampling_num = 0
	for user_id, all_dates in data_dict.items():
		real_user_id = user_id_index[user_id]
		one_user_profile = copy.deepcopy(profile[real_user_id])  # gender, age, edu, job
		one_user_profile.insert(0, user_id)        # insert user_id
		for date, activity in all_dates.items():
			for i in range(len(activity)):
				if 1:    #activity[i] != 'F':  # do not add 'F'
					sample = copy.deepcopy(one_user_profile)
					#del(sample[1:4])
					sample.append(i)  #(int(i/6))        # i represents hour
					sample.append(day_index[date])  # day_index: 7 days in one week
					feature.append(sample)
					category.append(activity[i])
					if is_over_sampling and len(sample) > 5:  # make sure that features are completed
						if activity[i] != 'F':
							sample_over = [[] for k in range(over_sampling_num)]
							for j in range(over_sampling_num):
								sample_over[j] = copy.deepcopy(sample)
								sample_over[j][-3] = random.randint(0, 8)  # random disturbance in job feature
								feature.append(sample_over[j])
								category.append(activity[i])
	return feature, category

# build features, all features
# False means test data do not need over sampling
def feature_build(train_dict, test_dict, profile, user_id_index):
	feature_train, category_train = feature_select(train_dict, profile, user_id_index, True)
	feature_test, category_test = feature_select(test_dict, profile, user_id_index, False)
	return feature_train, feature_test, category_train, category_test

# calculating the hit rate
def cal_hit_rate(category_predict, category_test):
	hit_count = 0
	sample_test_count = len(category_predict)
	for i in range(sample_test_count):
		if category_predict[i] == category_test[i]:
			hit_count += 1
	hit_rate = float(hit_count) / float(sample_test_count)
	print 'hit rate: ' + str(round(hit_rate, 4) * 100) + '%'

# calculating F value
def calculating_F_value(category_predict, category_test):
	n_predict = 0
	n_origin = 0
	hit_count = 0
	for item in category_predict:
		if item != 'F':
			n_predict += 1
	for item in category_test:
		if item != 'F':
			n_origin += 1
	for i in range(len(category_predict)):
		if category_predict[i] != 'F' and category_predict[i] == category_test[i]:
			hit_count += 1
	precision = float(hit_count) / float(n_predict)
	recall = float(hit_count) / float(n_origin)
	F_value = 2 * precision * recall / (precision + recall)
	print 'n_predict: ' + str(n_predict)
	print 'n_origin: ' + str(n_origin)
	print 'precision: ' + str(round(precision, 3))
	print 'recall: ' + str(round(recall, 3))
	print 'F_value: ' + str(round(F_value, 3))

# 1. select the service type using most in that period in past days
# 2. if user did not use service in that period before, select the service type using most in past days
# 3. if user did not use service before, select service randomly 
# service_count_hour: key = (user_id, hour, service_type) value = count
# service_count_past: key = (user_id, service_type)  value = count
# service_hour: key = (user_id, hour), value = [service_type, count]
# service_past: key = user_id, value = [service_type, count]
def conventional_method_Mused(feature_train, feature_test, category_train):
	service_count_hour = {}
	service_count_past = {}
	for i in range(len(feature_train)):
		key_hour = (feature_train[i][0], feature_train[i][5], category_train[i])
		if key_hour not in service_count_hour:
			service_count_hour[key_hour] = 1
		else:
			service_count_hour[key_hour] += 1

		key_past = (feature_train[i][0], category_train[i])
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

	category_predict = []
	for i in range(len(feature_test)):
		key_0 = (feature_test[i][0], feature_test[i][5])
		key_1 = feature_test[i][0]
		if key_0 in service_hour:
			value_0 = service_hour[key_0]
			category_predict.append(value_0[0])
		elif key_1 in service_past:
			value_1 = service_past[key_1]
			category_predict.append(value_1[0])
		else:
			random_num = random.randint(0, len(service_type)-1)
			category_predict.append(service_type[random_num])

	return category_predict
# method 2: service in last week
def conventional_method_Lweek(feature_train, feature_test, category_train):
	category_predict = ['FFF' for i in range(len(feature_test))]
	for i in range(len(feature_train)):
		sample = feature_train[i]
		user_id = sample[0]
		hour = sample[-2]
		date = sample[-1]
		if date == 0:    # 0 means it is Sunday and should be the last
			date = 7
		else:
			pass
		service_position = user_id * 168 + (date - 1) * 24 + hour
		category_predict[service_position] = category_train[i]
	return category_predict


# decision tree
def decision_tree(feature_train, feature_test, category_train):
	clf = tree.DecisionTreeClassifier()
	clf = clf.fit(feature_train, category_train)
	category_predict = clf.predict(feature_test)
	return category_predict

# save user_activity as pkl file for migration.py
def user_activity_save(user_activity, user_activity_path):
	output = open(user_activity_path, 'wb')
	pickle.dump(user_activity, output)
	output.close()

# user_activity is for migration.py
# key = user_id, range(1000), value = ['F', 'G'...], length is 7 * 24 = 168
def activity_restore(feature, category):
	user_activity = {}
	for i in range(USER_NUM):
		user_activity[i] = ['FFF' for j in range(168)]
	for i in range(len(feature)):
		sample = feature[i]
		user_id = sample[0]
		hour = sample[5]
		date = sample[-1]
		if date == 0:    # 0 means it is Sunday and should be the last
			date = 7
		else:
			pass
		position = (date - 1) * 24 + hour
		user_activity[user_id][position] = category[i]
	return user_activity

if __name__ == '__main__':
	'''
	activity_dict_path = '../data/activity_dict.pkl'
	activity_dict = get_activity_dict(activity_dict_path)
	train_dict_path = '../data/train_dict.pkl'
	test_dict_path = '../data/test_dict.pkl'
	user_id_index_path = '../data/user_id_index.pkl'
	data_segement(activity_dict, train_dict_path, test_dict_path, user_id_index_path)
	'''

	train_dict_path = '../data/train_dict.pkl'
	test_dict_path = '../data/test_dict.pkl'
	user_id_index_path = '../data/user_id_index.pkl'
	train_dict, test_dict, user_id_index = get_data(train_dict_path, test_dict_path, user_id_index_path)
	profile_path = '../data/profile.pkl'
	profile = get_profile(profile_path)

	feature_train, feature_test, category_train, category_test = feature_build(train_dict, test_dict, profile, user_id_index)
	print 'feature_train sample: ' + str(feature_train[1000])
	print 'feature_test sample: ' + str(feature_test[1000])



	# decision tree
	#category_Dtree = decision_tree(feature_train, feature_test, category_train)

	# conventional method: most-used service
	#category_Mused = conventional_method_Mused(feature_train, feature_test, category_train)

	# conventional method: last-week service
	category_Lweek = conventional_method_Lweek(feature_train, feature_test, category_train)

	cal_hit_rate(category_Lweek, category_test)
	calculating_F_value(category_Lweek, category_test)
	
	
	# this part is for migration.py
	'''
	# origin data, user_activity_origin is users' real behavior
	user_activity_origin_path = '../data/user_activity_test/user_activity_origin.pkl'
	user_activity_origin = activity_restore(feature_test, category_test)
	user_activity_save(user_activity_origin, user_activity_origin_path)
	'''
	'''
	# predition data using decision_tree
	user_activity_Dtree_path = '../data/user_activity_test/user_activity_Dtree.pkl'
	user_activity_Dtree = activity_restore(feature_test, category_Dtree)
	user_activity_save(user_activity_Dtree, user_activity_Dtree_path)
	'''
	'''
	# predition data according to users' most-used service
	user_activity_Mused_path = '../data/user_activity_test/user_activity_Mused.pkl'
	user_activity_Mused = activity_restore(feature_test, category_Mused)
	user_activity_save(user_activity_Mused, user_activity_Mused_path)
	'''

	
	# predition data according to users' last-week service
	user_activity_Lweek_path = '../data/user_activity_test/user_activity_Lweek.pkl'
	user_activity_Lweek = activity_restore(feature_test, category_Lweek)
	user_activity_save(user_activity_Lweek, user_activity_Lweek_path)
	