#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for activity cluster
# objective: To cluster different service
# JialongLi 2017/03/13

import re
import os
import sys
import pickle
import copy
reload(sys)
sys.setdefaultencoding( "utf-8" )
PERIOD = 1


# build dict for software_label and website_label
# software_dict: mark with G, S, V
# website_dict: mark with G, S, V
def build_dict(software_path, website_path):
	software_file = open(software_path, 'r')
	website_file = open(website_path, 'r')
	software_dict = {}
	website_dict = {}

	for line in software_file.readlines():
		item_list = line.decode('utf-8').strip().split('\t')
		if len(item_list) == 3:
			key = item_list[0]
			software_dict[key] = item_list[2]

	for line in website_file.readlines():
		item_list = line.decode('utf-8').strip().split('\t')
		if len(item_list) == 3:
			key = item_list[0]
			website_dict[key] = item_list[2]

	software_file.close()
	website_file.close()

	return software_dict, website_dict

# get profile: key: user_id, value = [gender, age, edu, job]
def get_profile(pkl_path):
	pkl_file = open(pkl_path, 'rb')
	profile = pickle.load(pkl_file)
	return profile

# activity dict initialization for all users
# user's activity: default value is 'down'
# format: {id_1:{'0507': [24/PERIOD], '0508': []}, id_2}
def activity_dict_init(profile):
	activity_dict = {}
	activity_date = {}
	for i in range(7, 14):
		if i < 10:
			key = '050' + str(i)
		else:
			key = '05' + str(i)
		activity_date[key] = ['down' for j in range(24 / PERIOD)]
	for i in range(4, 11):
		if i < 10:
			key = '060' + str(i)
		else:
			key = '06' + str(i)
		activity_date[key] = ['down' for j in range(24 / PERIOD)]
	for i in range(2, 9):
		key = '070' + str(i)
		activity_date[key] = ['down' for j in range(24 / PERIOD)]
	for i in range(6, 13):
		if i < 10:
			key = '080' + str(i)
		else:
			key = '08' + str(i)
		activity_date[key] = ['down' for j in range(24 / PERIOD)]

	for key in profile:
		activity_dict[key] = copy.deepcopy(activity_date)   # 不能使用赋值，否则都是使用同一个内存块
	return activity_dict

# identify service's type from one line
# service's type: W, G, S, V, idle, the computer is already 'on', so no 'down' here
def service_identify(item_list, software_dict, website_dict):
	time_pass = 0.0
	service_type = 'idle'
	software_key = 'None'
	website_key = 'None'
	action_valid = False

	if len(item_list) > 1:
		try:
			first_charater = item_list[0][0]
		except:
			first_charater = '0'
		if first_charater == 'T':
			action_valid = True
			time_pass = float(item_list[0].split('<=>')[1])


	if action_valid:
		if item_list[1][0] == 'P':
			software_key = (item_list[1].split('<=>'))[1]    # software's name
			if len(software_key) < 2:
				software_key = 'undefined'
		else:
			software_key = 'undefined'

		for item in item_list:
			if item[0] == 'U' and item != 'U<=>NULL':
				url_list = re.split('[\W]', item)

				if 'game' in url_list:                          # website's name 
					website_key = 'game'
				elif 'mail' in url_list:
					website_key = 'mail'
				elif 'com' in url_list:
					website_key = url_list[url_list.index('com') - 1]
				elif 'net' in url_list:
					website_key = url_list[url_list.index('net') - 1]
				elif 'cn' in url_list:
					website_key = url_list[url_list.index('cn') - 1]
				else:
					website_key = 'undefined'
				break

	if website_key != 'None':              
		if website_key in website_dict:
			service_type = website_dict[website_key]  # website_dict: G, S, V
		else:
			service_type = 'W'
	else:                                             # user is not using browser 
		if software_key in software_dict:
			service_type = software_dict[software_key]
		else:
			service_type = 'idle'

	return service_type, time_pass

# merge service in one period
# service_insert: list, element is set()
def service_merge(hour, minute, time_pass, service_type, service_insert):
	current_time = hour + minute / 60 + time_pass / 3600
	if current_time >= 24:
		current_time = 23.90
	index = int(current_time / PERIOD)
	service_insert[index].add(service_type)
	return service_insert

# activity build from service_insert
# category: 17
def activity_build(activity_dict, service_insert, date, user_id):
	cate = 'None'
	cate_W = '0'
	cate_G = '0'
	cate_S = '0'
	cate_V = '0'
	for i in range(24 / PERIOD):
		temp_set = service_insert[i]
		if len(temp_set) != 0:
			if 'W' in temp_set:
				cate_W = '1'
			else:
				cate_W = '0'
			if 'G' in temp_set:
				cate_G = '1'
			else:
				cate_G = '0'
			if 'S' in temp_set:
				cate_S = '1'
			else:
				cate_S = '0'
			if 'V' in temp_set:
				cate_V = '1'
			else:
				cate_V = '0'
			cate = cate_W + cate_G + cate_S + cate_V

			if cate == '0000' and 'idle' in temp_set: # only in this case can we call this period 'idle'
				cate = 'idle'

			activity_dict[user_id][date][i] = cate

		else:       # leave out, default is down
			pass
	return activity_dict


# build service for one user one day
def build_service(log_file_path, activity_dict, software_dict, website_dict, user_id):
	log_file = open(log_file_path, 'r')
	
	service_insert = [set() for i in range(24 / PERIOD)]

	line_num = 0
	time_last = 0.0
	date = '0507'
	hour = 0.0
	minute = 0.0
	for line in log_file.readlines():
		line = line.decode('utf-8').strip()
		if line_num == 0:
			item_list = line.split('<=>')
			time_last = float(item_list[1])
		elif line_num == 1:
			item_list = re.split('[\D]', line.split('<=>')[1])
			date = item_list[1] + item_list[2]
			hour = float(item_list[3])
			minute = float(item_list[4])
			if hour + minute / 60 + time_last / 3600 > 24.0:
				print 'time overflow'      # the log file cross two days
		else:
			item_list = line.split('[=]')
			service_type, time_pass = service_identify(item_list, software_dict, website_dict)
			service_insert = service_merge(hour, minute, time_pass, service_type, service_insert)
		line_num += 1

	activity_dict = activity_build(activity_dict, service_insert, date, user_id)
	log_file.close()
	return activity_dict

# save activity_dict as pkl file
def pkl_save(activity_dict, save_path):
	output = open(save_path, 'wb')
	pickle.dump(activity_dict, output)
	output.close()



if __name__ == '__main__':
	software_path = './data/software_label_0322.txt'
	website_path = './data/website_label_0322.txt'
	software_dict, website_dict = build_dict(software_path, website_path)

	root = 'C:/Users/lijialong94/Google Cloud/ML/project/data/behavior'
	#root = 'C:/Users/JialongLi/Google Cloud/ML/project/data/behavior'
	file_name_list = []
	dirs_list = []

	for roots, dirs, files in os.walk(root):
		if len(files) > 0:
			file_name_list.append(files)
		if len(dirs) > 0:
			dirs_list.append(dirs)
	dirs_list = dirs_list[0]

	pkl_path = './data/profile.pkl'
	profile = get_profile(pkl_path)
	activity_dict = activity_dict_init(profile)

	file_num = 0  # 18145 files in total
	for i in range(len(dirs_list)):
		one_folder = file_name_list[i]
		for j in range(len(one_folder)):
			user_id = one_folder[j].split('_')[0]
			log_file_path = root + './' + str(dirs_list[i]) + './' + str(one_folder[j])
			activity_dict = build_service(log_file_path, activity_dict, software_dict, website_dict, user_id)
			file_num += 1
			print file_num

	save_path = './data/activity_dict.pkl'
	pkl_save(activity_dict, save_path)

	print 'length of dict: ' + str(len(activity_dict))
	activity_temp = open('./data/activity_temp.txt', 'wb')
	for key_0, value_0 in activity_dict.items():
		activity_temp.write(key_0 + '\n')
		for key, value in value_0.items():
			activity_temp.write(key + '\t' + str(value) + '\n')
		activity_temp.write('\n')
	activity_temp.close()
