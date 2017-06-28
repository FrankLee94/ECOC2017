#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is cyclic-sleep
# objective: reducing energy consumption
# JialongLi 2017/05/23
# if there are no specific instructions, the unit of time is μs
# the minimum time unit is μs

import random
import math
import pickle
import copy
import time

ONU_NUM = 128
RTT = 100             # single trip, 0.1ms
UPSTREAM_RATE = 1e9   # 1000 Mbit/s
PERIOD_NUM = 168        # 168, 7 days, 7 * 24 hours
ONE_PERIOD = 1e7      # 1e7, 10s
SMALL_PERIOD = 1e6    # 1s
#T_SLEEP_LONG = 70 * 1000   # 50ms
#T_SLEEP_SHORT = 50 * 1000   # 20ms
T_AWAITING = 5000        # 5ms
T_RECOVERY = 2000       # 2ms
T_GUARD = 5             # 5μs
MAX_BUFFER = 5 * 1e5        # 1M
MAX_GRANT = 50000    # bit, 50μs, 50μs * 1e9 bit/s = 50000 bit 
ARRIVE_RATE_HIGH = 1000   # frames per second
ARRIVE_RATE_LOW = 10      # when user is off
INF = 1e10

global T_SLEEP_LONG
global T_SLEEP_SHORT

class Optical_Network_Unit:
	total_time = 0
	def __init__(self, grant, state, state_start_time, start_packet, end_packet, 
		total_sleep_time, total_packet, total_delay, sleep_time_select, packet_loss, last_packet, current_burden):
		self.grant = grant
		self.state = copy.deepcopy(state)
		self.state_start_time = copy.deepcopy(state_start_time)
		self.start_packet = start_packet
		self.end_packet = end_packet
		self.total_sleep_time = total_sleep_time
		self.total_packet = total_packet
		self.total_delay = total_delay
		self.sleep_time_select = sleep_time_select
		self.packet_loss = packet_loss
		self.last_packet = last_packet
		self.current_burden = current_burden

# ONU initialization
# state = [active, awaiting, recovery, sleep]
# state_start_time = [awaiting, recovery, sleep]
def ONU_initialization():
	global T_SLEEP_LONG
	Optical_Network_Unit.total_time = 0
	grant = 0
	state = [True, False, False, False]
	state_start_time = [INF, INF, INF]
	start_packet = -1
	end_packet = -1
	total_sleep_time = 0
	total_packet = 0
	total_delay = 0
	sleep_time_select = T_SLEEP_LONG
	packet_loss = 0
	last_packet = -1
	current_burden = 0

	ONU = []
	for i in range(ONU_NUM):
		ONU_object = Optical_Network_Unit(grant, state, state_start_time, start_packet, end_packet, 
		total_sleep_time, total_packet, total_delay, sleep_time_select, packet_loss, last_packet, current_burden)
		ONU.append(ONU_object)
	return ONU

# get user_status
# category_test, list, length = 168000
def get_user_status():
	category_predict_path = './category_predict_Lweek.pkl'
	category_test_path = './category_test.pkl'
	pkl_file_1 = open(category_predict_path, 'rb')
	category_predict = pickle.load(pkl_file_1)
	pkl_file_2 = open(category_test_path, 'rb')
	category_test = pickle.load(pkl_file_2)
	pkl_file_1.close()
	pkl_file_2.close()
	return category_predict, category_test

# rearrange the user status
def user_status_rearrange(category_predict, category_test):
	user_status_predict_all = [['F' for i in range(168)] for i in range(1000)]
	user_status_test_all = [['F' for i in range(168)] for i in range(1000)]
	for i in range(1000):
		for j in range(168):
			user_status_predict_all[i][j] = category_predict[i*168 + j]
			user_status_test_all[i][j] = category_test[i*168 + j]
	return user_status_predict_all, user_status_test_all

# get user_id
def get_user_id():
	user_id_path = './user_id_128.pkl'
	pkl_file = open(user_id_path, 'rb')
	user_id = pickle.load(pkl_file)
	pkl_file.close()
	return user_id

# select users
# user_id: list
def user_select(user_status_predict_all, user_status_test_all, user_id):
	user_status_predict = []
	user_status_test = []
	for i in user_id:
		user_status_predict.append(user_status_predict_all[i])
		user_status_test.append(user_status_test_all[i])
	return user_status_predict, user_status_test

# generate packets for a ONU in ONE_PERIOD
# ONE_PERIOD has 100 SMALL_PERIOD
def packet_generation(is_ONU_on):
	onu_packet = []
	time_stamp = []  # record the generation time of each packet
	time_index = 0
	small_period_index = 0
	while time_index < ONE_PERIOD:
		if is_ONU_on == True:
			arrive_rate_select = ARRIVE_RATE_HIGH
		else:        # ONU is off
			arrive_rate_select = ARRIVE_RATE_LOW

		Probability_Poisson = random.random()
		if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
			Probability_Poisson = 0.5
		interval = -(1e6 / arrive_rate_select) * math.log(1 - Probability_Poisson)   # generate a packet
		interval = int(round(interval))
		Probability_Uniform = random.random()
		packet_size = 64 + int (1454 * Probability_Uniform)  # byte
		time_index += interval       # generation time
		onu_packet.append(packet_size)
		time_stamp.append(time_index)
	return onu_packet, time_stamp

# generate packets for all ONU in ONE_PERIOD
def packet_generation_one_period(user_status_one_period):
	packet = [0 for i in range(ONU_NUM)]
	stamp = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		if user_status_one_period[i] == 'O':   # active
			is_ONU_on = True
		else:
			is_ONU_on = False
		onu_packet, time_stamp = packet_generation(is_ONU_on)
		packet[i] = copy.deepcopy(onu_packet)
		stamp[i] = copy.deepcopy(time_stamp)
	return packet, stamp

# change sleep time according to predict result
def sleep_time_change(ONU, user_status_one_period):
	global T_SLEEP_LONG
	global T_SLEEP_SHORT
	for i in range(ONU_NUM):
		if user_status_one_period[i] == 'O':
			ONU[i].sleep_time_select = T_SLEEP_SHORT
		else:
			ONU[i].sleep_time_select = T_SLEEP_LONG

# determine the transmission packet
# make sure that the time stamp of end packet can not be larger than absolute_clock
def grant_determine(ONU_object, onu_packet, time_stamp, absolute_clock):
	start_packet = ONU_object.start_packet
	end_packet = ONU_object.end_packet
	grant = 0
	if len(onu_packet) == 0 or len(onu_packet) - 1 == end_packet:
		start_packet = -1
		end_packet = -1
	else:
		while time_stamp[end_packet + 1] < absolute_clock:
			trans_packet_size = 8 * onu_packet[end_packet + 1]  # unit of oun_packet is byte
			if grant + trans_packet_size < MAX_GRANT:
				grant += trans_packet_size
				end_packet += 1
			else:
				break
			if len(onu_packet) - 1 == end_packet:
				break
		start_packet = ONU_object.end_packet + 1
	ONU_object.start_packet = start_packet
	ONU_object.end_packet = end_packet
	ONU_object.grant = grant
	ONU_object.current_burden -= grant

def mark_loss_packet(ONU_object, onu_packet, time_stamp, absolute_clock):
	packet_index = ONU_object.last_packet
	if len(onu_packet) == 0 or len(onu_packet) - 1 == packet_index:
		return
	if packet_index >= len(time_stamp) - 1:
		return

	while time_stamp[packet_index + 1] < absolute_clock:
		ONU_object.current_burden += 8 * onu_packet[packet_index + 1]
		if ONU_object.current_burden > MAX_BUFFER:
			ONU_object.packet_loss += 1
		packet_index += 1
		if packet_index >= len(onu_packet) - 1:
			break
	ONU_object.last_packet = packet_index

# report grant for the first time, absolute_clock = RTT
# grant does not surpass MAX_GRANT, in bit
def polling_init(ONU, packet, stamp, absolute_clock):
	for i in range(ONU_NUM):
		grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)

# packet transmission
def packet_transmission(ONU_object, absolute_clock):
	transmission_time = math.ceil(float(ONU_object.grant) / float(UPSTREAM_RATE))   # bit
	return int(transmission_time)

# packet delay: from packet arrive to transmission starts
def delay_calculation(ONU_object, time_stamp, absolute_clock):
	if ONU_object.start_packet > ONU_object.end_packet:  # no packet
		return
	else:
		for i in range(ONU_object.end_packet - ONU_object.start_packet + 1):
			ONU_object.total_delay += absolute_clock - time_stamp[ONU_object.start_packet + i]

# after each period (10s here), ONU needs to be reset. make sure that packet_delay...can not be reset
def reset(ONU):
	for i in range(ONU_NUM):
		ONU[i].grant = 0
		ONU[i].state[0] = True     # active
		ONU[i].state[1] = False
		ONU[i].state[2] = False
		ONU[i].state[3] = False
		ONU[i].state_start_time[0] = INF
		ONU[i].state_start_time[1] = INF
		ONU[i].state_start_time[2] = INF
		ONU[i].start_packet = -1
		ONU[i].end_packet = -1
		ONU[i].last_packet = -1
		ONU[i].current_burden = 0

# polling scheme
def polling(ONU, user_status_test, user_status_predict):
	for hour_index in range(24 * 7):
		user_status_one_period_real = [user_status_test[i][hour_index] for i in range(ONU_NUM)]
		user_status_one_period_predict = [user_status_predict[i][hour_index] for i in range(ONU_NUM)]
		packet, stamp = packet_generation_one_period(user_status_one_period_real)
		sleep_time_change(ONU, user_status_one_period_predict)

		absolute_clock = RTT        # before the first ONU sends data, the OLT needs to send a grant
		detect_all_sleep = absolute_clock   # when all ONU sleep, absolute_clock will not continue
		polling_init(ONU, packet, stamp, absolute_clock)   # report grant for the first time

		while absolute_clock < ONE_PERIOD:
			for i in range(ONU_NUM):
				if ONU[i].state[0] == True:    # active
					mark_loss_packet(ONU[i], packet[i], stamp[i], absolute_clock)
					transmission_time = packet_transmission(ONU[i], absolute_clock)
					delay_calculation(ONU[i], stamp[i], absolute_clock)
					absolute_clock += transmission_time
					grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)
					absolute_clock += T_GUARD
					if ONU[i].grant == 0:         # turn to awaiting state
						ONU[i].state[0] = False
						ONU[i].state[1] = True
						ONU[i].state_start_time[0] = absolute_clock
				elif ONU[i].state[1] == True:  # awaiting
					grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)
					if ONU[i].grant == 0:
						if absolute_clock - ONU[i].state_start_time[0] >= T_AWAITING: # awaiting to sleep
							ONU[i].state[1] = False
							ONU[i].state[3] = True
							ONU[i].state_start_time[0] = INF
							ONU[i].state_start_time[2] = absolute_clock
						else:
							pass
						absolute_clock += T_GUARD
					else:                   # awaiting to active
						ONU[i].state[1] = False
						ONU[i].state[0] = True
						ONU[i].state_start_time[0] = INF
					absolute_clock += T_GUARD
				elif ONU[i].state[2] == True:  # recovery
					if absolute_clock - ONU[i].state_start_time[1] >= T_RECOVERY: # recovery to active
						ONU[i].state[2] = False
						ONU[i].state[0] = True
						ONU[i].state_start_time[1] = INF
						grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)
						absolute_clock += T_GUARD
					else:
						pass
				else:        # sleep
					if absolute_clock - ONU[i].state_start_time[2] >= ONU[i].sleep_time_select:
						ONU[i].state[3] = False               # sleep to recovery
						ONU[i].state[2] = True
						ONU[i].total_sleep_time += absolute_clock - ONU[i].state_start_time[2]
						ONU[i].state_start_time[2] = INF
						ONU[i].state_start_time[1] = absolute_clock
					else:
						pass

			if detect_all_sleep == absolute_clock:  # make absolute_clock move when all ONUs sleep
				absolute_clock += T_GUARD
			else:
				pass
			detect_all_sleep = absolute_clock
			#print str(hour_index) + '\t' + str(absolute_clock)

		Optical_Network_Unit.total_time += ONE_PERIOD
		for i in range(ONU_NUM):
			ONU[i].total_packet += len(packet[i])
		reset(ONU)  # reset some parameters 

# statistics
def statistics(ONU):
	P_active = 6.35
	P_sleep = 0.7
	sum_packet = 0
	sum_delay = 0
	sum_sleep_time = 0
	sum_time = ONU_NUM * Optical_Network_Unit.total_time
	sum_packet_loss = 0
	for i in range(ONU_NUM):
		sum_packet += ONU[i].total_packet
		sum_delay += ONU[i].total_delay
		sum_sleep_time += ONU[i].total_sleep_time
		sum_packet_loss += ONU[i].packet_loss

	average_delay = int(sum_delay / sum_packet)
	average_energy = (P_sleep * sum_sleep_time + (sum_time - sum_sleep_time) * P_active) / float(sum_time)
	#print 'sum_delay' + '\t' + str(sum_delay)
	#print 'sum_packet' + '\t' + str(sum_packet)
	print 'sum_packet_loss' + '\t' + str(sum_packet_loss)
	loss_rate = float(sum_packet_loss) / float(sum_packet) * 10000
	print 'loss rate' + '\t' + str(loss_rate)
	#print 'simulation time' + '\t' + str(Optical_Network_Unit.total_time / 1e6) + 's'
	return average_delay, average_energy, loss_rate


def result_save(average_delay, average_energy):
	file_path = './result_10ms.txt'
	result_file = open(file_path, 'wb')
	result_file.write('sleep period' + '\t' + str(10) + 'ms' + '\n')
	result_file.write('average_delay' + '\t' + str(average_delay) + 'μs' + '\n')
	result_file.write('average_energy' + '\t' + str(average_energy) + 'W' + '\n')
	result_file.write('\n')
	result_file.write('ONU_NUM' + '\t' + str(ONU_NUM) + '\n')
	result_file.write('UPSTREAM_RATE' + '\t' + str(UPSTREAM_RATE) + '\n')
	result_file.write('PERIOD_NUM' + '\t' + str(PERIOD_NUM) + '\n')
	result_file.write('SMALL_PERIOD' + '\t' + str(SMALL_PERIOD) + 'μs' + '\n')
	result_file.write('T_AWAITING' + '\t' + str(T_AWAITING) + 'μs' + '\n')
	result_file.write('T_RECOVERY' + '\t' + str(T_RECOVERY) + 'μs' + '\n')
	result_file.write('MAX_GRANT' + '\t' + str(MAX_GRANT) + 'bit' + '\n')
	result_file.write('ARRIVE_RATE_HIGH' + '\t' + str(ARRIVE_RATE_HIGH) + '\n')
	result_file.write('ARRIVE_RATE_LOW' + '\t' + str(ARRIVE_RATE_LOW) + '\n')
	result_file.close()


if __name__ == '__main__':
	global T_SLEEP_LONG
	global T_SLEEP_SHORT
	T_SLEEP_LONG = 0
	T_SLEEP_SHORT = 0
	category_predict, category_test = get_user_status()
	user_status_predict_all, user_status_test_all = user_status_rearrange(category_predict, category_test)
	user_id = get_user_id()
	user_status_predict, user_status_test = user_select(user_status_predict_all, user_status_test_all, user_id)

	file_precise = open('./Lweek_128_3.txt', 'wb')
	#s_long = [25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 65, 68, 70, 73, 75, 80, 85, 90, 95, 100]
	s_long = [82, 84, 86, 88, 90, 92, 94, 96, 98, 100, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
	#s_short = [20, 5, 5, 10, 20, 10, 50, 50, 30, 80, 90, 60, 5, 10, 20, 10, 80, 30, 70, 60]
	for i in range(20):
		T_SLEEP_LONG =  s_long[i] * 1000      #(i + 1) * 5 * 1000
		#T_SLEEP_SHORT = (int(i / 10) + 1) * 20 * 1000  # 20, 40, 60
		T_SLEEP_SHORT = (int(i / 10) + 1) * 10 * 1000 + 70 * 1000

		start =time.clock()
		print 'group:  ' + str(i)
		print 'T_SLEEP_LONG' + '\t' + str(T_SLEEP_LONG / 1000) + 'ms'
		print 'T_SLEEP_SHORT' + '\t' + str(T_SLEEP_SHORT / 1000) + 'ms'
		print 'polling start'
		ONU = ONU_initialization()
		polling(ONU, user_status_test, user_status_predict)
		end = time.clock()
		average_delay, average_energy, loss_rate= statistics(ONU)
		average_energy = round(average_energy, 3)
		average_delay = float(average_delay) / 1000.0
		print 'average_delay' + '\t' + str(average_delay) + 'ms'
		print 'average_energy' + '\t' + str(average_energy) + 'W'
		#result_save(average_delay, average_energy)
		print 'running time' + '\t' + str(end - start) + 's'
		file_precise.write(str(i) + '\t' + str(average_delay) + 'ms' + '\t' + str(average_energy) + 'W' + '\t' + str(loss_rate) + '\n')

	file_precise.close()