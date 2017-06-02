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
UPSTREAM_RATE = 1e9   # 1000 Mbit/s
PERIOD_NUM = 1        # 168, 7 days, 7 * 24 hours
ONE_PERIOD = 1e7      # 1e8, 100s
SMALL_PERIOD = 1e6    # 1s
T_SLEEP_LONG = 50000   # 50ms
T_SLEEP_SHORT = 20000   # 20ms
T_AWAITING = 5000        # 5ms
T_RECOVERY = 2000       # 2ms
T_GUARD = 5             # 5μs
MAX_BUFFER = 1e7        # 10M
MAX_GRANT = 50000    # bit, 50μs, 50μs * 1e9 bit/s = 50000 bit 
ARRIVE_RATE = [10, 100, 1000, 10000]   # frames per second
INF = 1e10

class Optical_Network_Unit:
	def __init__(self, grant, state, state_start_time, start_packet, end_packet, 
		total_sleep_time, total_packet, total_delay, sleep_time_select):
		self.grant = grant
		self.state = state
		self.state_start_time = state_start_time
		self.start_packet = start_packet
		self.end_packet = end_packet
		self.total_sleep_time = total_sleep_time
		self.total_packet = total_packet
		self.total_delay = total_delay
		self.sleep_time_select = sleep_time_select

# ONU initialization
# state = [active, awaiting, recovery, sleep]
# state_start_time = [awaiting, recovery, sleep]
def ONU_initialization():
	grant = 0
	state = [True, False, False, False]
	state_start_time = [INF, INF, INF]
	start_packet = -1
	end_packet = -1
	total_sleep_time = 0
	total_packet = 0
	total_delay = 0
	sleep_time_select = T_SLEEP_SHORT
	
	ONU = []
	for i in range(ONU_NUM):
		ONU_object = Optical_Network_Unit(grant, state, state_start_time, start_packet, end_packet, 
		total_sleep_time, total_packet, total_delay, sleep_time_select)
		ONU.append(ONU_object)
	return ONU

# generate packets for a ONU in ONE_PERIOD
# ONE_PERIOD has 100 SMALL_PERIOD
def packet_generation():
	onu_packet = []
	time_stamp = []  # record the generation time of each packet
	time_index = 0
	small_period_index = 0
	arrive_rate_select = ARRIVE_RATE[random.randint(0, 3)]
	while time_index < ONE_PERIOD:
		if int(time_index / SMALL_PERIOD) != small_period_index:    # generate different arrive-rate packets
			small_period_index = int(time_index / SMALL_PERIOD)
			arrive_rate_select = ARRIVE_RATE[random.randint(0, 3)]
		else:
			pass
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
def packet_generation_one_period():
	packet = [0 for i in range(ONU_NUM)]
	stamp = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		print 'packet gneration for ONU:  ' + str(i)
		onu_packet, time_stamp = packet_generation()
		packet[i] = copy.deepcopy(onu_packet)
		stamp[i] = copy.deepcopy(time_stamp)
	return packet, stamp

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


# polling scheme
def polling(ONU):
	for hour_index in range(PERIOD_NUM):
		packet, stamp = packet_generation_one_period()

		absolute_clock = RTT        # before the first ONU sends data, the OLT needs to send a grant
		polling_init(ONU, packet, stamp, absolute_clock)   # report grant for the first time

		while absolute_clock < ONE_PERIOD:
			for i in range(ONU_NUM):
				if ONU[i].state[0] == True:    # active
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
			print absolute_clock

def test(a):
	a = 10
	return a


if __name__ == '__main__':

	ONU = ONU_initialization()
	polling(ONU)
	for i in range(ONU_NUM):
		print 'ONU:' + '\t' + str(i) + '\t' + str(ONU[i].total_sleep_time) + '\t' + str(ONU[i].total_delay)


