#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for migration
# objective: calculating traffic migration by different methods
# JialongLi 2017/03/28

import os
import sys
import pickle
import copy
import random

reload(sys)
sys.setdefaultencoding( "utf-8" )
USER_NUM = 1000
WAVE_NUM = 8
ONU_NUM = 32
USER_PER_ONU = 31
CAPACITY = 10.0
PERIOD_NUM = 168

service_traffic = {'I': 0.05, 'F': 0.0,  'W': 0.1, 'G': 0.1, 'S': 0.5, 'V': 0.5}  # unit: Gbps
day_index = ['0806', '0807', '0808', '0809', '0810', '0811', '0812']


# get test_dict
# user's activity: default value is 'off'
# format: {id_1:{'0507': [24/PERIOD], '0508': ['I', 'W', 'G']}, id_2}
# return test_dict
def get_test_dict(test_dict_path):
	pkl_file = open(test_dict_path, 'rb')
	test_dict = pickle.load(pkl_file)
	pkl_file.close()
	return test_dict

# convert one user's activity to a list
# 'idle' to 'I', 'off' to 'F'
# one_user_dict: dict, {'0507': [24/PERIOD], '0508': ['I', 'W', 'G']}
# return one_user_activity, list, length is 168
def activity_merge(one_user_dict):
	one_user_activity = []
	for day in day_index:
		for item in one_user_dict[day]:
			if item == 'idle':
				item = 'I'
			if item == 'off':
				item = 'F'
			one_user_activity.append(item)
	return one_user_activity

# convert id to number
# convert activity to a list
# one_user_activity: list, length is 168
# return user_activity: key = user_id, range(1000), value = ['F', 'G'...], length is 7 * 24 = 168
def test_dict_convert(test_dict):
	user_activity = {}
	user_index = 0
	for key, value in test_dict.items():
		one_user_activity = activity_merge(value)
		user_activity[user_index] = one_user_activity
		user_index += 1
	return user_activity

# assign user to onu
# USER_NUM, ONU_NUM
# return onu_id, range(ONU_NUM)
def map_user_onu(user_id):
	#onu_id = -1
	if user_id < 39:
		return 0
	else:
		return int(float(user_id - 39) / 31.0) + 1

# count service's type and total traffic in each period for each ONU
# onu_service: [[{'F':0, 'I':0, 'W':0, 'G':0, 'S':0, 'V':0 }, {}]], double list, element is dict
#              outer: 168 periods, inner: 32 ONUs
# onu_traffic: double list, outer: 168 periods, inner: 32 ONUs, element is float
# return onu_service, onu_traffic
def traffic_static(user_activity):
	onu_service = [[{'F':0, 'I':0, 'W':0, 'G':0, 'S':0, 'V':0} for i in range(ONU_NUM)] for j in range(PERIOD_NUM)]
	onu_traffic = [[0 for i in range(ONU_NUM)] for j in range(PERIOD_NUM)]

	onu_id = -1
	service_type = 'FFF'
	for i in range(PERIOD_NUM):
		for j in range(USER_NUM):
			onu_id = map_user_onu(j)
			service_type = user_activity[j][i]
			onu_service[i][onu_id][service_type] += 1
	for i in range(PERIOD_NUM):
		for j in range(ONU_NUM):
			for service_type, count in onu_service[i][j].items():
				onu_traffic[i][j] += service_traffic[service_type] * float(count)
	return onu_service, onu_traffic

# first fit algorithm
# onu_traffic: double list, outer: 168 periods, inner: 32 ONUs
# return the number of working wavelengths in all 168 periods
def first_fit(onu_traffic):
	working_wavelength = [1 for i in range(PERIOD_NUM)]
	for i in range(PERIOD_NUM):
		onu_traffic_sorted = copy.deepcopy(onu_traffic[i])
		onu_traffic_sorted = sorted(onu_traffic_sorted, reverse = True)
		current_volume = [0.0 for j in range(WAVE_NUM)]
		for j in range(ONU_NUM):
			is_need_new = True
			for k in range(working_wavelength[i]):         # found space in already-used wavelengths
				if current_volume[k] + onu_traffic_sorted[j] <= 10.0:
					current_volume[k] += onu_traffic_sorted[j]
					is_need_new = False
					break
			if is_need_new:               # need new wavelength
				working_wavelength[i] += 1
				current_volume[working_wavelength[i] - 1] += onu_traffic_sorted[j]
	return working_wavelength

# calculating migration between two periods
# previous_status and current_status: format: {0: [0, 2, 3], 1: [...]}, key is wavelength number and
# value is list containing ONU numbers associated with this wavelength
# return migration_one_period: {'I': 0.0, 'F': 0.0,  'W': 0.0, 'G': 0.0, 'S': 0.0, 'V': 0.0}
def cal_migration(previous_status, current_status, onu_service, period_id):
	migration_one_period = {'I': 0.0, 'F': 0.0,  'W': 0.0, 'G': 0.0, 'S': 0.0, 'V': 0.0}
	for key, value in current_status.items():
		for onu_id in value:
			if onu_id not in previous_status[key]:    # this onu has been migrated
				for service_type, count in onu_service[period_id][onu_id].items():
					migration_one_period[service_type] += float(count) * service_traffic[service_type]

	return migration_one_period

# return current status
def reconfiguration(previous_wavelength, current_wavelength, previous_status, onu_service, onu_traffic, period_id):
	current_status = copy.deepcopy(previous_status)
	pre_migrate_onu = set()    # contains onu waiting for re-loaded
	used_wavelength = set()    # wavelength No. used in previous status
	wavelength_diff = abs(current_wavelength - previous_wavelength)

	current_traffic = {}  # calculating the current burden in each wavelength
	for i in range(WAVE_NUM):
		current_traffic[i] = 0.0     # initialization
	for key, value in current_status.items():
		for onu_id in value:
			current_traffic[key] += onu_traffic[period_id][onu_id]
		if current_traffic[key] > 0.0:   # this wavelength is already used
			used_wavelength.add(key)

	current_traffic_sorted = sorted(current_traffic.items(), key=lambda current_traffic:current_traffic[1], reverse = True)

	if previous_wavelength > current_wavelength:  # shut down least-load wavelengths
		for i in range(wavelength_diff): # delete onus in least-load wavelength and add to pre_migrate_onu 
			least_load_wavelength = current_traffic_sorted[current_wavelength+i][0]
			for onu_id in current_status[least_load_wavelength]:
				pre_migrate_onu.add(onu_id)
			current_status[least_load_wavelength] = []
			used_wavelength.remove(least_load_wavelength)  # remove the shut down wavelength
	else:
		for i in range(wavelength_diff):    # add more wavelength
			for j in range(WAVE_NUM):
				if j not in used_wavelength:
					used_wavelength.add(j)
					break

	for key, value in current_status.items():#examine current burden in each wavelength, adjust overflowed wavelength
		onu_traffic_perwave = {}
		for onu_id in value:
			onu_traffic_perwave[onu_id] =  onu_traffic[period_id][onu_id]

		if current_traffic[key] > 10.001: # overflow, reload it; due to float precision problem,set 10.0001 here
			current_traffic[key] = 0.0
			onu_traffic_perwave_sorted = sorted(onu_traffic_perwave.items(), key=lambda onu_traffic_perwave:onu_traffic_perwave[1], reverse = True)
			current_status[key] = []
			index = 0
			while current_traffic[key] + onu_traffic_perwave_sorted[index][1] <= 10.0:
				current_status[key].append(onu_traffic_perwave_sorted[index][0])
				current_traffic[key] += onu_traffic_perwave_sorted[index][1]
				index += 1
			for i in range(index, len(onu_traffic_perwave_sorted)):
				pre_migrate_onu.add(onu_traffic_perwave_sorted[i][0])
		else:
			pass

	# load the pre_migrate_onu in descending order
	pre_migrate_traffic = {}
	for onu_id in pre_migrate_onu:
		pre_migrate_traffic[onu_id] = onu_traffic[period_id][onu_id]
	pre_migrate_traffic_sorted = sorted(pre_migrate_traffic.items(), key=lambda pre_migrate_traffic:pre_migrate_traffic[1], reverse = True)

	for item in pre_migrate_traffic_sorted:    # sorted in descending order by traffic
		is_pack = False
		for wave_id in used_wavelength:
			if item[1] + current_traffic[wave_id] <= 10.0:
				current_traffic[wave_id] += item[1]
				current_status[wave_id].append(item[0])
				is_pack = True
				break
		if not is_pack:
			for i in range(WAVE_NUM):
				if i in used_wavelength:
					pack_position = i
					#print 'not pack'
					break      # pick a already-used wavelength randomly
			current_traffic[pack_position] += item[1]
			current_status[wave_id].append(item[0])

	return current_status

# migration
# previous_status: dict, keys are wavelength number, value is list contains ONUs associated with this wavelength
# current_status: the same as previous_status, format: {0: [0, 2, 2], 1: [...]}
# format: {0: [0, 2, 2], 1: [...]}
def migration(working_wavelength, onu_service, onu_traffic):
	migration_count = {'I': [], 'F': [],  'W': [], 'G': [], 'S': [], 'V': []}

	previous_status = {}
	for i in range(WAVE_NUM):   # initialization
		previous_status[i] = []
		if i == 0:              # the start of time is 0:00 and use only one wavelength
			for j in range(ONU_NUM):
				previous_status[i].append(j)

	for i in range(PERIOD_NUM - 1):
		current_status = reconfiguration(working_wavelength[i], working_wavelength[i+1], previous_status, onu_service, onu_traffic, i+1)
		migration_one_period = cal_migration(previous_status, current_status, onu_service, i+1)
		previous_status = copy.deepcopy(current_status)
		for service_type in migration_count:
			migration_count[service_type].append(migration_one_period[service_type])
		print 'period num: ' + str(i+1)
	
	return migration_count

if __name__ == '__main__':
	'''
	test_dict_path = '../data/test_dict.pkl'
	test_dict = get_test_dict(test_dict_path)
	user_activity = test_dict_convert(test_dict)
	onu_service, onu_traffic = traffic_static(user_activity)
	working_wavelength = first_fit(onu_traffic)

	status_tuple = (working_wavelength, onu_service, onu_traffic)
	save_path = '../data/status_tuple.pkl'
	output = open(save_path, 'wb')
	pickle.dump(status_tuple, output)
	output.close()
	'''

	save_path = '../data/status_tuple.pkl'
	pkl_file = open(save_path, 'rb')
	status_tuple = pickle.load(pkl_file)
	pkl_file.close()
	working_wavelength = status_tuple[0]
	onu_service = status_tuple[1]
	onu_traffic = status_tuple[2]

	migration_count = migration(working_wavelength, onu_service, onu_traffic)
	for key, value in migration_count.items():
		print key, value