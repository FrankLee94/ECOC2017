#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for drawing user states
# JialongLi 2017/07/09

import pickle 

# category_test: length = 168000
def get_category_test():
	out_file = open('./category_test.pkl', 'rb')
	category_test = pickle.load(out_file)
	out_file.close()
	return category_test

def get_user_state(category_test, user_id, out_file):
	for i in range(user_id * 168, user_id * 168 + 168):
		if category_test[i] == 'O':
			out_file.write('1' + '\n')
		else:
			out_file.write('0' + '\n')
	out_file.close()

def create_index_file():
	index_file = open('../user_state/index.txt', 'wb')
	for i in range(168):
		index_file.write(str(i) + '\n')
	index_file.close()

if __name__ == '__main__':
	create_index_file()
	category_test = get_category_test()
	user_id = 918
	out_file = open('../user_state/' + str(user_id) + '.txt', 'wb')
	get_user_state(category_test, user_id, out_file)