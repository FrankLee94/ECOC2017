#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for activity identification
# objective: To extract running programs and websites
# JialongLi 2017/03/10

import re
import os
import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )

# extract running programs and websites
def extract(file_path, software_count, website_count):
	activity_file = open(file_path, 'r')
	line_num = 0
	for line in activity_file.readlines():
		item_list = line.decode('utf-8').split('[=]')

		line_num += 1
		#print line_num

		action_valid = False
		if len(item_list) > 1:
			try:
				first_charater = item_list[0][0]
			except:
				first_charater = '0'
			if first_charater == 'T':
				action_valid = True

		if action_valid:
			if item_list[1][0] == 'P':
				software_key = (item_list[1].split('<=>'))[1]    # software's name
				if len(software_key) < 2:
					software_key = 'undefined'
			else:
				software_key = 'undefined'
			if software_key not in software_count:
				software_count[software_key] = 1
			else:
				software_count[software_key] += 1

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

					if website_key not in website_count:
						website_count[website_key] = 1
					else:
						website_count[website_key] += 1
					break
	activity_file.close()


# save running programs and websites
def save(software_path, website_path, software_count, website_count):
	software_file = open(software_path, 'w')
	website_file = open(website_path, 'w')
	software_count_sorted = sorted(software_count.items(), key=lambda software_count:software_count[1], reverse=True)
	website_count_sorted = sorted(website_count.items(), key=lambda website_count:website_count[1], reverse=True)

	for i in range(len(software_count_sorted)):
		s_item = software_count_sorted[i]
		software_file.write(str(s_item[0]) + '\t' + str(s_item[1]) + '\t' + '\n')

	for i in range(len(website_count_sorted)):
		w_item = website_count_sorted[i]
		website_file.write(str(w_item[0]) + '\t' + str(w_item[1]) + '\t' + '\n')

	software_file.close()
	website_file.close()


if __name__ == '__main__':
	root = 'C:/Users/lijialong94/Google Cloud/ML/project/data/behavior'
	file_name_list = []
	dirs_list = []

	for roots, dirs, files in os.walk(root):
		if len(files) > 0:
			file_name_list.append(files)
		if len(dirs) > 0:
			dirs_list.append(dirs)
	dirs_list = dirs_list[0]

	software_count = {}
	website_count = {}

	'''
	file_num = 0
	for i in range(len(dirs_list)):
		one_folder = file_name_list[i]
		for j in range(len(one_folder)):
			file_path = root + './' + str(dirs_list[i]) + './' + str(one_folder[j])
			extract(file_path, software_count, website_count)
			file_num += 1
			print file_num
	'''

	user_0AC = '0AC18D27CC2284445BC249E8A83462FE'
	file_num = 0
	for i in range(len(dirs_list)):
		one_folder = file_name_list[i]
		for j in range(len(one_folder)):
			if one_folder[j].split('_')[0] == user_0AC:
				file_path = root + './' + str(dirs_list[i]) + './' + str(one_folder[j])
				extract(file_path, software_count, website_count)
				file_num += 1
				print file_num

	software_path = 'C:/Users/lijialong94/Google Cloud/ML/project/data/software_0AC.txt'
	website_path = 'C:/Users/lijialong94/Google Cloud/ML/project/data/website_0AC.txt'
	save(software_path, website_path, software_count, website_count)

