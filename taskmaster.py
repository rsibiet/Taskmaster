#!/usr/bin/python3.4
# -*-coding:UTF-8 -*

import sys
import os
import cmd
import yaml
import subprocess
import time
import signal
import datetime
import shlex
from threading import Thread

global log
try:
	log = open("/tmp/taskmaster.log", "w")
except Exception as e:
	print(e.args)
	sys.exit()
global oldDico
oldDico = {}
program = {}
log.close()

def logReport(towrite):
	global log
	try:
		log = open("/tmp/taskmaster.log", "a")
	except Exception as e:
		print(e.args)
	if log.closed == False:
		log.write(towrite)
		log.close()

class Programm:

	def __init__(self, arg):
		self.flag = True
		self.fail = False
		self.started = False
		self.stopped = False
		self.stoppedTime = 0
		self.arg = arg
		self.tab = {
			'cmd': "false",
			'numprocs': 1,
			'umask': "022",
			'workingdir': ".",
			'autostart': False,
			'autorestart': "unexpected",
			'exitcodes': [1],
			'startretries': 1,
			'starttime': 1,
			'stopsignal': "TERM",
			'stoptime': 0,
			'stdout': 1,
			'stderr': 2,
			'env': "none"
		}
		self.signal = {
			'INT': signal.SIGINT,
			'QUIT': signal.SIGQUIT,
			'KILL': signal.SIGKILL,
			'ABRT': signal.SIGABRT,
			'TERM': signal.SIGTERM,
			'TSTP': signal.SIGTSTP,
		}
		if self.parse(arg, self.tab) == False:
			print("Parse error")
			sys.exit()
		if self.tab["autostart"] == True:
			self.start("Starting")
		if self.tab['env'] != 'none':
			for key in self.tab['env']:
				os.environ[key] = str(self.tab['env'][key])
	def nbProcess(self):
		if str(self.tab["numprocs"]).isdigit() == False or self.tab["numprocs"] < 0 or self.tab["numprocs"] > 10:
			self.tab["numprocs"] = 1
		i = 0
		while i < int(self.tab['numprocs']):
			self.process.append(0)
			i += 1
		self.time = datetime.datetime.now()

	def parse(self, arg, tab):
		if arg != None:
			for key, val in arg.items():
				ret = False
				for i in tab:
					if (key == i):
						ret = True
						tab[key] = val
					if (key == "starttime" or key == "stoptime") and (str(tab[key]).isdigit() == False or tab[key] < 0):
						tab[key] = 0
				if ret == False:
					return False
		self.process = []
		self.nbProcess();
		if self.tab["stdout"] != 1:
			try:
				self.fout = open(self.tab["stdout"], "w+")
			except Exception as e:
				print (self.tab['cmd'], " out file: ", e.args, "Default file: stdout")
				self.fout = open(self.tab['workingdir'] + "/" + "stdout", "w+")
		else:
			self.fout = 1
		if self.tab["stderr"] != 2:
			try:
				self.ferr = open(self.tab["stderr"], "w+")
			except Exception as e:
				self.ferr = open(self.tab['workingdir'] + "/" + "stderr", "w+")
				print (self.tab['cmd'], " ferr file: ", e.args, "Default file: stdout")
			if os.path.exists(self.tab['workingdir']) == False:
				print (self.tab['cmd'], " Working directory: failure. " "Default dir: .")
				self.tab['workingdir'] = "."
		else:
			self.ferr = 2
		return True
	def status(self, cmdName):
		i = 0
		timeAct = datetime.datetime.now()
		diffTime =  timeAct - self.time
		while i < self.tab['numprocs']:
			print("\033[95m", cmdName, "\033[0m", end='')
			if self.process[i] != 0 and self.tab["starttime"] <= diffTime.total_seconds():
				print("\033[92m RUNNING       pid: ", self.process[i].pid, ", uptime: \033[0m", str(diffTime)[:7])
			elif self.tab["starttime"] > diffTime.total_seconds() and self.process[i] != 0:
				print("\033[93m STARTED       pid: ", self.process[i].pid, ", uptime: \033[0m", str(diffTime)[:7])
			elif self.fail == True and self.process[i] != 0:
				print("\033[91m FAILED AT RUNTIME\033[0m")
			else:
				print("\033[97m NOT RUNNING\033[0m")
			i += 1
	def initchildproc(self):
		os.umask(int(self.tab['umask']))

	def checkState(self):
		i = 0
		ret = True
		badexit = True
		while i < self.tab['numprocs']:
			if self.process[i] != 0:
				if self.process[i].poll() != None:
					self.process[i].wait()
					exitcode = self.process[i].returncode
					for j in self.tab['exitcodes']:
						if exitcode == j:
							self.fail = False
							badexit = False
							self.process[i] = 0;
							logReport("Program: " + self.tab['cmd'] + " Correctly stopped " + str(datetime.datetime.now())[:19] + "\n\n")
							break
						badexit = True
						j += 1
					if badexit == True:
						self.fail = True
						logReport("Program: " + self.tab['cmd'] + " Badly killed " + str(datetime.datetime.now())[:19] + "\n\n")
						ret = False
						self.process[i] = 0;
			i += 1
		return ret

	def start(self, line):
		global log
		logReport(line + " program: " + self.tab['cmd'] + " " + str(datetime.datetime.now())[:19] + "...\n\n")
		self.time = datetime.datetime.now()
		i = 0
		while i < self.tab['numprocs']:
			if self.process[i] == 0:
				try:
					j = 0
					while j < self.tab['startretries']:
						self.process[i] = subprocess.Popen( shlex.split(self.tab["cmd"]), shell=False, stdout=self.fout, stderr=self.ferr, cwd=self.tab['workingdir'], preexec_fn=self.initchildproc)
						if self.process[i].poll() == None:
							logReport("\tProgram: " + self.tab['cmd'] + " Started " + str(datetime.datetime.now())[:19] + "\n")
							self.started = True
							self.stopped = False
							break
						j += 1
					if i == self.tab['startretries']:
						self.fail = True
						logReport("\tProgram: " + self.tab['cmd'] + " Fail to started " + str(datetime.datetime.now())[:19] + "\n")
				except Exception as inst:
					print(inst.args)
					sys.exit(1)
			i += 1
		return True
	def restart(self):
		self.stop()
		self.start("Restarting")
	def stop(self):
		if self.stopped == False:
			self.stopped = True
			self.stoppedTime = datetime.datetime.now()
		actTime = datetime.datetime.now()
		diffTime = actTime - self.stoppedTime

		if diffTime.total_seconds() >= self.tab['stoptime']:
			i = 0
			while i < self.tab['numprocs']:
				if self.process[i] != 0:
					self.process[i].send_signal(self.signal[self.tab["stopsignal"]])
					self.process[i].wait()
					logReport("Program: " + self.tab['cmd'] + " Stopped " + str(datetime.datetime.now())[:19] + "\n\n")
					self.process[i] = 0
				i += 1
	def force_stop(self):
		i = 0
		while i < self.tab['numprocs']:
			if self.process[i] != 0:
				self.process[i].send_signal(signal.SIGKILL)
				self.process[i].wait()
				self.process[i] = 0
				logReport("Program: " + self.tab['cmd'] + " Stopped " + str(datetime.datetime.now())[:19] + "\n\n")
			i += 1

program = dict()

class ProcChecker(Thread):
	"""docstring forProcChecker."""
	def __init__(self, arg):
		 Thread.__init__(self)
		 self.exit = False
	def run(self):
			while self.exit == False:
				time.sleep(1)
				for x in program:
					if program[x].checkState() == False:
						if (program[x].tab['autorestart'] == "excepted" and program[x].started == True) or (program[x].tab['autorestart'] == 'unexpected' and program[x].fail == True):
							program[x].start("restarting")
					if program[x].stopped == True:
						program[x].stop()

class loop_cmd(cmd.Cmd):
	def __init__(self):
		cmd.Cmd.__init__(self)

	def do_start(self, line):
		if line != "":
			try:
				program[line].start("Starting")
			except:
				print("program[" + line + "] doest not exist")
		else:
			print("start command: Usage: start <program name>")

	def do_status(self, line):
		for x in program:
			if program[x].flag == True:
				program[x].status(x)

	def do_stop(self, line):
		if line != "":
			try:
				program[line].stop()
			except:
				print("program[" + line + "] doest not exist")
		else:
			print("stop command: Usage: stop <program name>")

	def do_restart(self, line):
		if line != "":
			try:
				program[line].restart()
			except:
				print("program[" + line + "] doest not exist")
		else:
			print("restart command: Usage: restart <program name>")
	def do_exit(self, line):
		for x in program:
			program[x].force_stop()
		thread_1.exit = True
		logReport("\t\t*******...EXITING TASKMASTER...********\n")
		log.close()
		sys.exit()

	def do_reload(self, line):
		dico = {}
		global oldDico
		try:
			with open(sys.argv[1]) as dict:
				dico = yaml.load(dict)
		except Exception as e:
			print(e.args)
			sys.exit()
		for x in program:
			try:
				if dico[x] == False:
					dico[x] = True;
			except:
				program[x].stop()
				program[x].flag = False
		for x in dico:
			if x in program:
				if x in oldDico:
					if oldDico[x] != dico[x]:
						program[x].force_stop()
						program[x].parse(dico[x], program[x].tab)
						logReport(x + " Realoded " + str(datetime.datetime.now())[:19] + "\n")
						program[x].restart()
				else:
					program[x] = Programm(dico[x])
			else:
				program[x] = Programm(dico[x])
		oldDico = dico.copy()

	def do_clear(self, line):
		log = open("/tmp/log", "w")
		log.close()

	def do_stopAll(self, line):
		for x in program:
			program[x].force_stop()

	def do_EOF(self, line):
		self.do_exit(line)


thread_1 = ProcChecker("coucou")

def handler(signum, frame):
	for x in program:
		program[x].force_stop()
	thread_1.exit = True
	thread_1.join()
	sys.exit()

def main(av):
	logReport("\t\t*******...RUNNING TASKMASTER...********\n\n\n")
	dico = {}
	i = 1
	signal.signal(signal.SIGSEGV, handler)
	signal.signal(signal.SIGINT, handler)
	signal.signal(signal.SIGTERM, handler)
	signal.signal(signal.SIGABRT, handler)
	signal.signal(signal.SIGBUS, handler)
	signal.signal(signal.SIGQUIT, handler)
	signal.signal(signal.SIGILL, handler)
	signal.signal(signal.SIGTSTP, handler)
	try:
		with open(av) as dict:
			dico = yaml.load(dict)
	except Exception as e:
		print(e.args)
		sys.exit()
	thread_1.start()
	global oldDico
	oldDico = dico.copy()
	for x in dico:
		program[x] = Programm(dico[x])
	loop_cmd().cmdloop()

if len(sys.argv) != 2:
	print("Taskmaster: Usage: python3 taskmaster <configuration file>")
else:
	main(sys.argv[1])
