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


ONU_NUM = 32
RTT = 100             # single trip, 0.1ms
ARRIVE_RATE = 40000   # frames per second
GUARD_TIME = 5        # 5μs
UPSTREAM_RATE = 1e10  # 10000 Mbit/s
POLLING_CYCLE = 1000  # 1ms
ONE_PERIOD = 1e6      # 1s
FIXED_GRANT = 50      # 50μs


# generate packets for a ONU in 1s
def packet_generation():
	onu_packet = []
	time_stamp = []  # record the generation time of each packet
	index = 0
	while index < ONE_PERIOD:
		Probability_Poisson = random.random()
		if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
			Probability_Poisson = 0.5
		interval = -(1e6 / ARRIVE_RATE) * math.log(1 - Probability_Poisson)   # generate a packet
		interval = int(round(interval))
		Probability_Uniform = random.random()
		packet_size = 64 + int (1454 * Probability_Uniform)  # byte
		index += interval       # generation time
		onu_packet.append(packet_size)
		time_stamp.append(index)
	return onu_packet, time_stamp


# polling each ONU at the beginning
def initialization():
	packet = [0 for i in range(ONU_NUM)]
	stamp = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		onu_packet, time_stamp = packet_generation()
		packet[i] = copy.deepcopy(onu_packet)
		time_stamp[i] = copy.deepcopy(time_stamp)
	return packet, stamp

# determine the transmission packet
# make sure that the time stamp of end packet can not be larger than absolute_clock
def packet_transmission(onu_packet, time_stamp, absolute_clock, end_packet):
	grant_data = FIXED_GRANT * UPSTREAM_RATE * 1e-6    # bit
	real_data = 0
	while real_data < grant_data:
		if len(onu_packet) > end_packet:   # packet still exists
			if time_stamp[end_packet + 1] < absolute_clock:
				end_packet += 1
				real_data += 8 * onu_packet[end_packet]    # unit of oun_packet is byte
		else:
			break
	return end_packet



def polling(total_time):
	absolute_clock = 0
	absolute_clock += RTT   # before the first ONU sends data, the OLT needs to send a grant
	window_index = [[0, 0] for i in range(ONU_NUM)]  # indicating the start packet and end packet
	waiting_time = [[] for i in range(ONU_NUM)]     # queue delay
	packet, stamp = initialization()

	polling_num = 0
	end_packet = 0
	while absolute_clock < total_time:
		for i in range(ONU_NUM):
			start_packet, end_packet = packet_transmission(packet[i], stamp[i], absolute_clock, end_packet)
			queue_delay = calculating_delay()      # queue delay
			waiting_time[i].append(queue_delay)
			absolute_clock += FIXED_GRANT + GUARD_TIME
			
		polling_num += 1

if __name__ == '__main__':

	#absolute_clock, onu_clock, buffers = initialization()

	total_time = 1e6
	packet, stamp = initialization()
	for i in range(ONU_NUM):
		print len(packet[i])
	#absolute_clock, buffers = polling(total_time, absolute_clock, onu_clock, buffers)




