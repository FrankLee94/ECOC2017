#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is cyclic-sleep
# objective: reducing energy consumption
# JialongLi 2017/05/23
# if there are no specific instructions, the unit of time is μs

import random
import math

ONU_NUM = 32
RTT = 100.0  # single trip
ARRIVE_RATE = 1000  # frames per second

def packet_generation():
	Probability_Poisson = random.random()
	if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
		Probability_Poisson = 0.5
	interval = -(1e6 / ARRIVE_RATE) * math.log(1 - Probability_Poisson)   # generate a packet
	Probability_Uniform = random.random()
	packet_size = 512 + int (11632 * Probability_Uniform)  # bit
	return interval, packet_size


# polling each ONU at the beginning
def initialization():
	absolute_clock = 0.0
	onu_clock = [0.0 for i in range(ONU_NUM)]
	buffers = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		while onu_clock[i] < RTT * (2 * i + 1):
			interval, packet_size = packet_generation()
			onu_clock[i] += interval
			buffers[i] += packet_size 
		absolute_clock += RTT * 2
	return absolute_clock, onu_clock, buffers





if __name__ == '__main__':
	absolute_clock, onu_clock, buffers = initialization()
	print absolute_clock
	print onu_clock
	print buffers
	

