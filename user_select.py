#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is user select
# objective: select users
# JialongLi 2017/06/13

import pickle
import random
USER_SELECT_POOL_NUM = 300


# get user_status
# category_test, list, length = 168000
def get_user_status():
	category_predict_Dtree_path = './category_predict_Dtree.pkl'
	category_predict_Lweek_path = './category_predict_Lweek.pkl'
	category_test_path = './category_test.pkl'
	pkl_file_1 = open(category_predict_Dtree_path, 'rb')
	category_predict_Dtree = pickle.load(pkl_file_1)
	pkl_file_2 = open(category_predict_Lweek_path, 'rb')
	category_predict_Lweek = pickle.load(pkl_file_2)
	pkl_file_3 = open(category_test_path, 'rb')
	category_test = pickle.load(pkl_file_3)
	pkl_file_1.close()
	pkl_file_2.close()
	pkl_file_3.close()
	return category_predict_Dtree, category_predict_Lweek, category_test

# rearrange the user status
def user_status_rearrange(category_predict_Dtree, category_predict_Lweek, category_test):
	user_status_predict_Dtree_all = [['F' for i in range(168)] for i in range(1000)]
	user_status_predict_Lweek_all = [['F' for i in range(168)] for i in range(1000)]
	user_status_test_all = [['F' for i in range(168)] for i in range(1000)]
	for i in range(1000):
		for j in range(168):
			user_status_predict_Dtree_all[i][j] = category_predict_Dtree[i*168 + j]
			user_status_predict_Lweek_all[i][j] = category_predict_Lweek[i*168 + j]
			user_status_test_all[i][j] = category_test[i*168 + j]
	return user_status_predict_Dtree_all, user_status_predict_Lweek_all, user_status_test_all

# calculating rate for dividual users
def rate_calculating(user_status_predict_Dtree_all, user_status_predict_Lweek_all, user_status_test_all):
	file_rate = open('./rate_ONU.txt', 'wb')
	rate_Dtree_dict = {}
	rate_Lweek_dict = {}
	rate_diff_dict = {}
	for i in range(1000):
		count_Dtree = 0
		count_Lweek = 0
		for j in range(168):
			if user_status_predict_Dtree_all[i][j] == user_status_test_all[i][j]:
				count_Dtree += 1
			if user_status_predict_Lweek_all[i][j] == user_status_test_all[i][j]:
				count_Lweek	+= 1
		rate_Dtree = round(float(count_Dtree) / float(168) * 100, 2)
		rate_Lweek = round(float(count_Lweek) / float(168) * 100, 2)
		rate_diff = rate_Dtree - rate_Lweek
		rate_Dtree_dict[i] = rate_Dtree
		rate_Lweek_dict[i] = rate_Lweek
		rate_diff_dict[i] = round(rate_diff, 4)
		file_rate.write(str(i) + '\t' + str(rate_Dtree) + '%' + '\t' + 
			str(rate_Lweek) + '%'+ '\t' + str(rate_diff) + '%' + '\n')
	file_rate.close()
	return rate_Dtree_dict, rate_Lweek_dict, rate_diff_dict

# pick users
def user_pick(rate_Dtree_dict, rate_Lweek_dict, rate_diff_dict):
	user_pool_id = []
	rate_diff_dict_sorted = sorted(rate_diff_dict.items(), key=lambda rate_diff_dict:rate_diff_dict[1], reverse = True)
	id_index = 0
	item_index = 0
	for item in rate_diff_dict_sorted:
		user_id = item[0]
		item_index += 1
		if rate_Dtree_dict[user_id] > 78.0 and rate_Lweek_dict[user_id] > 0.0:
			user_pool_id.append(user_id)
			id_index += 1
		if id_index >= USER_SELECT_POOL_NUM:
			print 'select completely'
			print 'item index' + '\t' + str(item_index)
			break
	return user_pool_id

def statistic(user_pool_id, user_status_predict_Dtree_all, user_status_test_all):
	on_on_total = 0
	on_off_total = 0
	off_on_total = 0
	off_off_total = 0
	for user_id in user_pool_id:
		for hour in range(168):
			if user_status_test_all[user_id][hour] == 'O' and user_status_predict_Dtree_all[user_id][hour] == 'O':
				on_on_total += 1
			elif user_status_test_all[user_id][hour] == 'O' and user_status_predict_Dtree_all[user_id][hour] == 'F':
				on_off_total += 1
			elif user_status_test_all[user_id][hour] == 'F' and user_status_predict_Dtree_all[user_id][hour] == 'O':
				off_on_total += 1
			else:
				off_off_total += 1
	item_total = 168 * len(user_pool_id)
	on_on_rate = round(float(on_on_total) / float(item_total) * 100, 4)
	on_off_rate = round(float(on_off_total) / float(item_total) * 100, 4)
	off_on_rate = round(float(off_on_total) / float(item_total) * 100, 4)
	off_off_rate = round(float(off_off_total) / float(item_total) * 100, 4)
	hit_rate = on_on_rate + off_off_rate
	print 'on_on_rate' + '\t' + str(on_on_rate) + '%'
	print 'on_off_rate' + '\t' + str(on_off_rate) + '%'
	print 'off_on_rate' + '\t' + str(off_on_rate) + '%'
	print 'off_off_rate' + '\t' + str(off_off_rate) + '%'
	print 'hit_rate' + '\t' + str(hit_rate) + '%'
	return hit_rate

# save user_id for sleep.py
def save_file_for_sleep(user_pool_id_select, file_path):
	output = open(file_path, 'w')
	pickle.dump(user_pool_id_select, output)
	output.close()


if __name__ == '__main__':
	'''
	category_predict_Dtree, category_predict_Lweek, category_test = get_user_status()
	user_status_predict_Dtree_all, user_status_predict_Lweek_all, user_status_test_all = user_status_rearrange(category_predict_Dtree, category_predict_Lweek, category_test)
	rate_Dtree_dict, rate_Lweek_dict, rate_diff_dict = rate_calculating(user_status_predict_Dtree_all, user_status_predict_Lweek_all, user_status_test_all)
	user_pool_id = user_pick(rate_Dtree_dict, rate_Lweek_dict, rate_diff_dict)

	print 'overall Dtree statistic'
	hit_rate_1 = statistic(user_pool_id, user_status_predict_Dtree_all, user_status_test_all)
	print 'overall Lweek statistic'
	hit_rate_2 = statistic(user_pool_id, user_status_predict_Lweek_all, user_status_test_all)
	print 'diff' + '\t' + str(hit_rate_1 - hit_rate_2)

	print '\n'
	print 'random test 128'
	random.shuffle(user_pool_id)
	user_pool_id_select = user_pool_id[0 : 128]
	print 'length' + '\t' + str(len(user_pool_id_select))
	print 'overall Dtree statistic'
	hit_rate_1 = statistic(user_pool_id_select, user_status_predict_Dtree_all, user_status_test_all)
	print 'overall Lweek statistic'
	hit_rate_2 = statistic(user_pool_id_select, user_status_predict_Lweek_all, user_status_test_all)
	print 'diff' + '\t' + str(hit_rate_1 - hit_rate_2)
	file_path_1 = './user_id_128_2.pkl'
	save_file_for_sleep(user_pool_id_select, file_path_1)
	print 'user_id_128'
	print user_pool_id_select

	print '\n'
	print 'random test 256'
	random.shuffle(user_pool_id)
	user_pool_id_select = user_pool_id[0 : 256]
	print 'length' + '\t' + str(len(user_pool_id_select))
	print 'overall Dtree statistic'
	hit_rate_1 = statistic(user_pool_id_select, user_status_predict_Dtree_all, user_status_test_all)
	print 'overall Lweek statistic'
	hit_rate_2 = statistic(user_pool_id_select, user_status_predict_Lweek_all, user_status_test_all)
	print 'diff' + '\t' + str(hit_rate_1 - hit_rate_2)

	file_path_2 = './user_id_256_2.pkl'
	save_file_for_sleep(user_pool_id_select, file_path_2)
	print 'user_id_256'
	print user_pool_id_select
	'''