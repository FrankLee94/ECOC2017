#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for user profile
# objective: To extract user profile
# JialongLi 2017/03/18

# gender 男：0, 女：1
# age   >90:0, 70-90:1, <70:2 
# edu  小学/初中：0， 高中/中专/技校/大专/：1， 大学本科/硕士及以上/: 2
# job   学生:0, 无业下岗失业,退休：1， 专业技术人员:2
#       党政机关事业单位一般职员：3， 农村外出务工人员：4
#       企业/公司管理者：5  党政机关事业单位领导干部：6  个体户/自由职业者：7
#       企业/公司一般职员: 8
#       其他：9

# profile format: dict, key = real_id, value = [gender, age, edu, job]

import sys
import csv
reload(sys)
sys.setdefaultencoding( "utf-8" )
import pickle
FEATURE_RAW_DATA_COUNT = 9

def get_profile(file_path):
	csvfile = file(file_path, 'rb')
	reader = csv.reader(csvfile)
	profile = {}
	gender = 0
	age = 0
	edu = 0
	job = 0

	line_num = 0
	for line in reader:
		if line_num == 0:
			line_num += 1
			continue

		for i in range(FEATURE_RAW_DATA_COUNT):
			if line[1] == '男':
				gender = 0
			else:
				gender = 1

			if int(line[2]) > 1990:
				age = 0
			elif int(line[2]) < 1970:
				age = 2
			else:
				age = 1

			if line[3] == '小学及以下' or line[3] == '初中':
				edu = 0
			elif line[3] == '高中/中专/技校' or line[3] == '大专':
				edu = 1
			elif line[3] == '大学本科' or line[3] == '硕士及以上':
				edu = 2
			else:
				print 'education classification wrong'

			if line[4] == '学生':
				job = 0
			elif line[4] == '无业、下岗、失业' or line[4] == '退休':
				job = 1
			elif line[4] == '专业技术人员':
				job = 2
			elif line[4] == '党政机关事业单位一般职员' or line[4] == '党政机关事业单位工作者':
				job = 3
			elif line[4] == '农村外出务工人员' or line[4] == '农民':
				job = 4
			elif line[4] == '企业/公司管理者':
				job = 5
			elif line[4] == '党政机关事业单位领导干部':
				job = 6
			elif line[4] == '个体户/自由职业者':
				job = 7
			elif line[4] == '企业/公司一般职员' or line[4] == '产业、服务业工人':
				job = 8
			elif line[4] == '其他':
				job = 9
			else:
				'job classification wrong'

			key = line[0]
			profile[key] = []
			profile[key].append(gender)
			profile[key].append(age)
			profile[key].append(edu)
			profile[key].append(job)
	return profile

def pkl_save(profile, save_path):
	output = open(save_path, 'wb')
	pickle.dump(profile, output)
	output.close()

if __name__ == '__main__':
	file_path = '../data/demographic.csv'
	save_path = '../data/profile.pkl'
	profile = get_profile(file_path)
	pkl_save(profile, save_path)
