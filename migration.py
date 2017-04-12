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
import matplotlib.pyplot as plt
import pylab as pl
import numpy as np

reload(sys)
sys.setdefaultencoding( "utf-8" )
USER_NUM = 1000
WAVE_NUM = 32
ONU_NUM = 32
USER_PER_ONU = 31
CAPACITY = 10.001
PERIOD_NUM = 168

service_traffic = {'I': 0.05, 'F': 0.0,  'W': 0.1, 'G': 0.1, 'S': 0.5, 'V': 0.5}  # unit: Gbps
day_index = ['0806', '0807', '0808', '0809', '0810', '0811', '0812']


# assign user to onu
# USER_NUM, ONU_NUM
# return onu_id, range(ONU_NUM)
def map_user_onu(user_id):
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
		onu_traffic_sorted = sorted(onu_traffic[i], reverse = True)
		current_volume = [0.0 for j in range(WAVE_NUM)]
		for j in range(ONU_NUM):
			is_need_new = True
			for k in range(working_wavelength[i]):         # found space in already-used wavelengths
				if current_volume[k] + onu_traffic_sorted[j] <= CAPACITY:
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
# origin method
def reconfiguration_origin(previous_wavelength, current_wavelength, previous_status, onu_service, onu_traffic, period_id):
	current_status = copy.deepcopy(previous_status)
	pre_migrate_onu = set()    # contains onu waiting for re-loaded
	used_wavelength = set()    # wavelength No. used in previous status
	wavelength_diff = abs(current_wavelength - previous_wavelength)

	current_burden = {}  # calculating the current burden in each wavelength
	for i in range(WAVE_NUM):
		current_burden[i] = 0.0     # initialization
	for key, value in current_status.items():
		for onu_id in value:
			current_burden[key] += onu_traffic[period_id][onu_id]
		if current_burden[key] > 0.0:   # this wavelength is already used
			used_wavelength.add(key)

	current_burden_sorted = sorted(current_burden.items(), key=lambda current_burden:current_burden[1], reverse = True)

	if previous_wavelength > current_wavelength:  # shut down least-load wavelengths
		for i in range(wavelength_diff): # delete onus in least-load wavelength and add to pre_migrate_onu 
			least_load_wavelength = current_burden_sorted[current_wavelength+i][0]
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

		if current_burden[key] > CAPACITY: # overflow, reload it; due to float precision problem,set CAPACITY001 here
			current_burden[key] = 0.0
			onu_traffic_perwave_sorted = sorted(onu_traffic_perwave.items(), key=lambda onu_traffic_perwave:onu_traffic_perwave[1], reverse = True)
			current_status[key] = []
			index = 0
			while current_burden[key] + onu_traffic_perwave_sorted[index][1] <= CAPACITY:
				current_status[key].append(onu_traffic_perwave_sorted[index][0])
				current_burden[key] += onu_traffic_perwave_sorted[index][1]
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
			if item[1] + current_burden[wave_id] <= CAPACITY:
				current_burden[wave_id] += item[1]
				current_status[wave_id].append(item[0])
				is_pack = True
				break
		if not is_pack:
			for i in range(WAVE_NUM):
				if i in used_wavelength:
					pack_position = i
					#print 'not pack'
					break      # pick a already-used wavelength randomly
			current_burden[pack_position] += item[1]
			current_status[wave_id].append(item[0])

	return current_status

# migration
# previous_status: dict, keys are wavelength number, value is list contains ONUs associated with this wavelength
# current_status: the same as previous_status, format: {0: [0, 2, 3], 1: [...]}
# format: {0: [0, 2, 3], 1: [...]}
# migration_one_period: traffic migration, {'I': 0.0, 'F': 0.0,  'W': 0.0, 'G': 0.0, 'S': 0.0, 'V': 0.0}, 
# migration_count: dict, value is list, length of value is 167, migration traffic in each period
def migration_origin(working_wavelength, onu_service, onu_traffic):
	migration_count = {'I': [], 'F': [],  'W': [], 'G': [], 'S': [], 'V': []}
	previous_status = {}
	for i in range(WAVE_NUM):   # initialization
		previous_status[i] = []
		if i == 0:              # the start of time is 0:00 and use only one wavelength
			for j in range(ONU_NUM):
				previous_status[i].append(j)

	for i in range(PERIOD_NUM - 1):
		current_status = reconfiguration_origin(working_wavelength[i], working_wavelength[i+1], previous_status, onu_service, onu_traffic, i+1)
		migration_one_period = cal_migration(previous_status, current_status, onu_service, i+1)
		previous_status = copy.deepcopy(current_status)
		for service_type in migration_count:
			migration_count[service_type].append(migration_one_period[service_type])
		print 'period num: ' + str(i+1)
	return migration_count

# migration performance: calculating different traffic migration in all periods
# migration_count: dict, value is list, length of value is 167
def migration_static(migration_count, onu_traffic, working_wavelength_real):
	migration_traffic = {'I': 0, 'F': 0,  'W': 0, 'G': 0, 'S': 0, 'V': 0}
	energy = 0
	for key, value in migration_count.items():
		for item in value:
			migration_traffic[key] += item
	total_migration = 0
	for key, value in migration_traffic.items():
		total_migration += value
	total_traffic = 0
	for period in onu_traffic:
		for item in period:
			total_traffic += item
	for item in working_wavelength_real:
		energy += item
	print 'migration traffic'
	for key, value in migration_traffic.items():
		print key, value
	print 'total migration: ' + str(total_migration)
	print 'total traffic: ' + str(total_traffic)
	print 'migration rate: ' + str(round(total_migration / total_traffic, 4) * 100) + '%'
	print 'energy consumption: ' + str(energy)

# sort onu_id in one wavelength by delay-sensitive traffic for reconfiguring in one wavelength
# onu_list: onu_id in a wavelength
def sort_onu_id_delay(onu_list, onu_service, period_id):
	onu_id_delay_traffic = {}    # only delay-sensitive traffic is calculated
	onu_id_delay = []
	for onu_id in onu_list:
		one_onu_service = onu_service[period_id][onu_id]
		onu_id_delay_traffic[onu_id] = 0.0
		for key, value in one_onu_service.items():
			if key == 'S' or key == 'G':   # delay-sensitive traffic
				onu_id_delay_traffic[onu_id] += float(value) * service_traffic[key]
	onu_id_delay_traffic_sorted = sorted(onu_id_delay_traffic.items(), key=lambda onu_id_delay_traffic:onu_id_delay_traffic[1], reverse = True)
	for item in onu_id_delay_traffic_sorted:
		onu_id_delay.append(item[0])
	return onu_id_delay

# sort onu_id in pre_migrate_onu by overall traffic for relocating pre_migrate_onu	
def sort_onu_id_overall(pre_migrate_onu, onu_traffic, period_id):
	onu_id_overall_traffic = {}    # overall traffic is calculated
	onu_id_overall = []
	for onu_id in pre_migrate_onu:
		onu_id_overall_traffic[onu_id] = onu_traffic[period_id][onu_id]
	onu_id_overall_traffic_sorted = sorted(onu_id_overall_traffic.items(), key=lambda onu_id_overall_traffic:onu_id_overall_traffic[1], reverse = True)
	for item in onu_id_overall_traffic_sorted:
		onu_id_overall.append(item[0])
	return onu_id_overall

# sort wavelength by delay-sensitive traffic for shutting down reference
def sort_wave_id_delay(used_wavelength, current_status, onu_service, period_id):
	wave_id_delay_traffic = {}
	wave_id_delay = []
	for wave_id in used_wavelength:
		wave_id_delay_traffic[wave_id] = 0.0
		for onu_id in current_status[wave_id]:
			one_onu_service = onu_service[period_id][onu_id]
			onu_id_delay_traffic = 0.0
			for key, value in one_onu_service.items():
				if key == 'S' or key == 'G':   # delay-sensitive traffic
					onu_id_delay_traffic += float(value) * service_traffic[key]
			wave_id_delay_traffic[wave_id] += onu_id_delay_traffic
	wave_id_delay_traffic_sorted = sorted(wave_id_delay_traffic.items(), key=lambda wave_id_delay_traffic:wave_id_delay_traffic[1], reverse = True)
	for item in wave_id_delay_traffic_sorted:
		wave_id_delay.append(item[0])
	return wave_id_delay

# sort wavelength by overall traffic for shutting down reference
def sort_wave_id_overall(used_wavelength, current_burden):
	wave_id_overall_traffic = {}
	wave_id_overall = []
	for wave_id in used_wavelength:
		wave_id_overall_traffic[wave_id] = current_burden[wave_id]
	wave_id_overall_traffic_sorted = sorted(wave_id_overall_traffic.items(), key=lambda wave_id_overall_traffic:wave_id_overall_traffic[1], reverse = True)
	for item in wave_id_overall_traffic_sorted:
		wave_id_overall.append(item[0])
	return wave_id_overall

# get shutdown wavelength, shutdown_wave_num: number of shutdown wavelength
# shutdown_wavelength: set
def get_shutdown_wavelength(wave_id_overall, shutdown_wave_num):
	shutdown_wavelength_set = set()
	for i in range(shutdown_wave_num):
		shutdown_wavelength_id = wave_id_overall[-(i+1)]
		shutdown_wavelength_set.add(shutdown_wavelength_id)
	return shutdown_wavelength_set

# get onu_in_shutdown_wave, format: set
# shutdown_wavelength: set; onu_in_shutdown_wave: set
def get_onu_in_shudown_wave(shutdown_wavelength_set, current_status_temp):
	onu_in_shutdown_wave = set()
	for shutdown_wavelength_id in shutdown_wavelength_set:
		for onu_id in current_status_temp[shutdown_wavelength_id]:
			onu_in_shutdown_wave.add(onu_id)
	return onu_in_shutdown_wave

# when a onu_id associate with a wavelength_id, decide whether the wavelength will overflow
def predict_next_status(onu_id, wavelength_id, current_status, onu_traffic_predict, period_id):
	is_future_overflow = False
	wavelength_id_next_burden = 0.0
	for onu_id in current_status[wavelength_id]:
		wavelength_id_next_burden += onu_traffic_predict[period_id + 1][onu_id]
	wavelength_id_next_burden += onu_traffic_predict[period_id + 1][onu_id]
	if wavelength_id_next_burden > CAPACITY :
		is_future_overflow = True
	else:
		is_future_overflow = False
	return False # is_future_overflow

# examine current burden in each wavelength, adjust overflowed wavelength
# pre_migrate_onu: set, contains onu_id from overflowed wavelength
# current_status: key = wave_id, value = list contains onu_id; overflowed onu_id have been moved
# current_burden: key = wave_id, value = overall traffic;  overflowed onu_id have been moved
# used_wavelength: set, contains wavelength_id being used
def reconfiguration_initial(previous_status, onu_service, onu_traffic, period_id):
	current_status = copy.deepcopy(previous_status)
	pre_migrate_onu = set()    # contains onu waiting for re-located
	used_wavelength = set()    # wavelength No. used
	current_burden = {}  # calculating the current burden in each wavelength
	for i in range(WAVE_NUM):
		current_burden[i] = 0.0     # initialization, for all WAVE_NUM wavelengths
	for key, value in current_status.items():
		for onu_id in value:
			current_burden[key] += onu_traffic[period_id][onu_id]

	for key, value in current_status.items():#examine current burden in each wavelength, adjust overflowed wavelength
		onu_id_overall = sort_onu_id_overall(value, onu_traffic, period_id)  # sorted onu_id by overall traffic
		if current_burden[key] > CAPACITY: # overflow, reload it; due to float precision problem,set 10.001 here
			current_burden[key] = 0.0
			current_status[key] = []
			for i in range(len(onu_id_overall)): # add onu in decending order of overall traffic
				onu_id = onu_id_overall[i]
				if current_burden[key] + onu_traffic[period_id][onu_id] <= CAPACITY:
					current_status[key].append(onu_id)
					current_burden[key] += onu_traffic[period_id][onu_id]
				else:
					pre_migrate_onu.add(onu_id)
		else:
			pass
	for key, value in current_status.items():
		if len(value) > 0:
			used_wavelength.add(key)  # this wavelength is already used
	return pre_migrate_onu, current_status, current_burden, used_wavelength

# relocate pre_migrate_onu collecting from overflowed wavelengths
def relocate_pre_migrate_onu(pre_migrate_onu, current_status, current_burden, used_wavelength, onu_traffic, period_id):
	onu_id_overall = sort_onu_id_overall(pre_migrate_onu, onu_traffic, period_id)  # list
	for i in range(len(onu_id_overall)):
		onu_id = onu_id_overall[i]
		is_locate = False
		for wavelength_id in used_wavelength:
			is_future_overflow = predict_next_status(onu_id, wavelength_id, current_status, onu_traffic_predict, period_id)
			if current_burden[wavelength_id] + onu_traffic[period_id][onu_id] <= CAPACITY and not is_future_overflow:
				current_status[wavelength_id].append(onu_id)
				current_burden[wavelength_id] += onu_traffic[period_id][onu_id]
				pre_migrate_onu.remove(onu_id)
				is_locate = True
				break
		if not is_locate:
			for new_wave in range(WAVE_NUM):
				if new_wave not in used_wavelength:
					used_wavelength.add(new_wave)
					current_status[new_wave].append(onu_id)
					current_burden[new_wave] += onu_traffic[period_id][onu_id]
					pre_migrate_onu.remove(onu_id)
					break
	if len(pre_migrate_onu) != 0:   # pre_migrate_onu should be empty
		print 'reconfiguration error when traffic increase'
	return current_status, current_burden, used_wavelength

# try to shutdown some wavelengths while migration do not occur in next status
def shutdown_attempt(current_status, current_burden, used_wavelength, onu_traffic, period_id):
	for shutdown_wave_num in range(len(used_wavelength)): # shutdown_wave's range
		current_status_temp = copy.deepcopy(current_status)
		current_burden_temp = copy.deepcopy(current_burden)
		used_wavelength_temp = copy.deepcopy(used_wavelength)
		wave_id_overall = sort_wave_id_overall(used_wavelength_temp, current_burden_temp)
		shutdown_wavelength_set = get_shutdown_wavelength(wave_id_overall, shutdown_wave_num)
		used_wavelength_temp = used_wavelength_temp - shutdown_wavelength_set # shutdown wavelengths
		onu_in_shutdown_wave = get_onu_in_shudown_wave(shutdown_wavelength_set, current_status_temp)
		onu_id_overall = sort_onu_id_overall(onu_in_shutdown_wave, onu_traffic, period_id)
		max_shutdown_wave = shutdown_wave_num
		is_shutdown_end = False
		for i in range(len(onu_id_overall)):
			onu_id = onu_id_overall[i]
			is_locate = False
			for wavelength_id in used_wavelength_temp:
				is_future_overflow = predict_next_status(onu_id, wavelength_id, current_status_temp, onu_traffic_predict, period_id)
				if current_burden_temp[wavelength_id] + onu_traffic[period_id][onu_id] <= CAPACITY and not is_future_overflow:
					current_status_temp[wavelength_id].append(onu_id)
					current_burden_temp[wavelength_id] += onu_traffic[period_id][onu_id]
					onu_in_shutdown_wave.remove(onu_id)
					is_locate = True
					break
			if not is_locate:
				is_shutdown_end = True
				break
		if is_shutdown_end:
			max_shutdown_wave = shutdown_wave_num - 1
			break
	print 'max_shutdown_wave: ' + str(max_shutdown_wave)
	if max_shutdown_wave < 0:
		print 'error in shutdown_attempt'
	return max_shutdown_wave

# current_status, working_wavelength_real = shutdown_relocate(max_shutdown_wave, period_id)
def shutdown_relocate(current_status, current_burden, used_wavelength, onu_traffic, max_shutdown_wave, period_id):
	wave_id_overall = sort_wave_id_overall(used_wavelength, current_burden)
	shutdown_wavelength_set = get_shutdown_wavelength(wave_id_overall, max_shutdown_wave)
	used_wavelength = used_wavelength - shutdown_wavelength_set # shutdown wavelengths
	onu_in_shutdown_wave = get_onu_in_shudown_wave(shutdown_wavelength_set, current_status)
	onu_id_overall = sort_onu_id_overall(onu_in_shutdown_wave, onu_traffic, period_id)
	for i in range(len(onu_id_overall)):
		onu_id = onu_id_overall[i]
		is_locate = False
		for wavelength_id in used_wavelength:
			is_future_overflow = predict_next_status(onu_id, wavelength_id, current_status, onu_traffic_predict, period_id)
			if current_burden[wavelength_id] + onu_traffic[period_id][onu_id] <= CAPACITY and not is_future_overflow:
				current_status[wavelength_id].append(onu_id)
				current_burden[wavelength_id] += onu_traffic[period_id][onu_id]
				onu_in_shutdown_wave.remove(onu_id)
				is_locate = True
				break
		if not is_locate:
			print 'error in shutdown_relocate 1'
			break
	if len(onu_in_shutdown_wave) != 0:
		print 'error in shutdown_relocate 2'
	working_wavelength_real = len(used_wavelength)
	return current_status, working_wavelength_real

# return current status
# reconfiguration method based on prediction data, details can be referred to notebook
# current_status: format: {0: [0, 2, 3], 1: [...]}
def reconfiguration_Dtree(previous_status, onu_service, onu_traffic, 
	onu_traffic_predict, period_id):
	pre_migrate_onu, current_status, current_burden, used_wavelength = reconfiguration_initial \
	(previous_status, onu_service, onu_traffic, period_id)   #overflowed onu_id have been moved

	current_status, current_burden, used_wavelength = relocate_pre_migrate_onu(pre_migrate_onu, current_status, current_burden, used_wavelength, onu_traffic, period_id)
	max_shutdown_wave = shutdown_attempt(current_status, current_burden, used_wavelength, onu_traffic, period_id)
	current_status, working_wavelength_real = shutdown_relocate(current_status, current_burden, used_wavelength, onu_traffic, max_shutdown_wave, period_id)
	return current_status, working_wavelength_real

# migration using prediction data, including Dtree, Lweek, Mused.
# previous_status: dict, keys are wavelength number, value is list contains ONUs associated with this wavelength
# current_status: the same as previous_status, format: {0: [0, 2, 2], 1: [...]}
# format: {0: [0, 2, 2], 1: [...]}
def migration_Dtree(onu_service, onu_traffic, onu_traffic_predict):
	migration_count = {'I': [], 'F': [],  'W': [], 'G': [], 'S': [], 'V': []}
	previous_status = {}
	working_wavelength_real = []
	for i in range(WAVE_NUM):   # initialization
		previous_status[i] = []
		if i == 0:              # the start of time is 0:00 and use only one wavelength
			for j in range(ONU_NUM):
				previous_status[i].append(j)

	for i in range(PERIOD_NUM - 2):
		current_status, working_wavelength_real_temp = reconfiguration_Dtree \
			(previous_status, onu_service, onu_traffic, onu_traffic_predict, i+1)
		migration_one_period = cal_migration(previous_status, current_status, onu_service, i+1)
		previous_status = copy.deepcopy(current_status)
		working_wavelength_real.append(working_wavelength_real_temp)
		for service_type in migration_count:
			migration_count[service_type].append(migration_one_period[service_type])
		print 'period num: ' + str(i+1)
	return migration_count, working_wavelength_real

# get user_activity
def get_user_activity(user_activity_path):
	pkl_file = open(user_activity_path, 'rb')
	user_activity = pickle.load(pkl_file)
	pkl_file.close()
	return user_activity


if __name__ == '__main__':
	# user_activity format: key = range(1000), value = list contains service type, length = 168

	user_activity_origin_path = '../data/user_activity_test/user_activity_origin.pkl'
	user_activity_Dtree_path = '../data/user_activity_test/user_activity_Dtree.pkl'
	user_activity_Lweek_path = '../data/user_activity_test/user_activity_Lweek.pkl'
	user_activity_Mused_path = '../data/user_activity_test/user_activity_Mused.pkl'
	user_activity_origin = get_user_activity(user_activity_origin_path)
	user_activity_Dtree = get_user_activity(user_activity_Dtree_path)
	user_activity_Lweek = get_user_activity(user_activity_Lweek_path)
	user_activity_Mused = get_user_activity(user_activity_Mused_path)

	onu_service, onu_traffic = traffic_static(user_activity_origin)
	working_wavelength = first_fit(onu_traffic)


	# conventional method
	# migration_count = migration_origin(working_wavelength, onu_service, onu_traffic)
	# migration_static(migration_count, onu_traffic)

	# predition method by real data
	onu_service_predict = copy.deepcopy(onu_service)
	onu_traffic_predict = copy.deepcopy(onu_traffic)
	migration_count, working_wavelength_real = migration_Dtree(onu_service, onu_traffic, onu_traffic_predict)
	migration_static(migration_count, onu_traffic, working_wavelength_real)
	
	energy = 0
	for item in working_wavelength:
		energy += item
	print 'origin energy consumption: ' + str(energy)
	print working_wavelength
	print working_wavelength_real

	print max(max(onu_traffic))
	'''
	n = [i for i in range(168)]
	traffic_period = [0.0 for i in range(PERIOD_NUM)]
	traffic_period_predict = [0.0 for i in range(PERIOD_NUM)]
	for i in range(PERIOD_NUM):
		for item in onu_traffic[i]:
			traffic_period[i] += item
		for item in onu_traffic_predict[i]:
			traffic_period_predict[i] += item
	plt.plot(n, traffic_period, color = 'red')
	plt.plot(n, traffic_period_predict, color = 'blue')
	plt.show()
	'''