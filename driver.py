#!/usr/bin/python3
import sys
import logging
import os
import paramiko
import threading
import random
import time
from pexpect import pxssh

#Default Values
dbserver='localhost'  
password='password123'
username='guest'
number_of_users=10    #Number of concurrent users
file_list=[]          #List of files to read/write
max_btime=120         #minutes
min_btime=2           #minutes
max_interactive=120   #minutes
min_interactive=2     #minutes
think_time=2          #seconds
rampup_time=1         #seconds
active_users=10

#Variables for file copy



logger = logging.getLogger('driver')
format = "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
logging.basicConfig(format=format,level=logging.INFO)


def initialize(filename):
	logger.info("START: Config file")
	f=open(filename,"r")
	lines = f.readlines()
	for line in lines:
		args=line.split("=")

		if args[0] == "DBSERVER":
			global dbserver
			dbserver=args[1].rstrip()
		elif args[0] == "PASSWORD":
			global password
			password=args[1].rstrip()
		elif args[0] == "USERNAME":
			global username
			username=args[1].rstrip()
		elif args[0] == "NO_USERS":
			global number_of_users
			number_of_users=int(args[1].rstrip())
		elif args[0] == "ACTIVE_USERS":
			global active_users
			active_users=int(args[1].rstrip())
		elif args[0] == "FILE_LIST":
			global file_list
			file_list=args[1].rstrip().split(',')
		elif args[0] == "MIN_BATCH_TIME":
			global min_btime
			min_btime=int(args[1].rstrip())
		elif args[0] == "MAX_BATCH_TIME":
			global max_btime
			max_btime=int(args[1].rstrip())
		elif args[0] == "MIN_INTERATIVE_TIME":
			global min_interactive
			min_interactive=int(args[1].rstrip())
		elif args[0] == "MAX_INTERATIVE_TIME":
			global max_interactive
			max_interactive=int(args[1].rstrip())
		elif args[0] == "INTERATIVE_THINK_TIME":
			global think_time
			think_time=int(args[1].rstrip())
		elif args[0] == "RAMPUP_TIME":
			global rampup_time
			rampup_time=int(args[1].rstrip())
	
	f.close()
	logger.info("END: Config file")	
	logger.info('ConfigFile: dbserver:'+dbserver)
	logger.info('ConfigFile: password: '+password)
	logger.info('ConfigFile: username: '+username)
	logger.info('ConfigFile: number_of_users: '+str(number_of_users))
	logger.info('ConfigFile: file_list: '+str(file_list))
	logger.info('ConfigFile: min_btime: '+str(min_btime))
	logger.info('ConfigFile: max_btime: '+str(max_btime))
	logger.info('ConfigFile: min_interactive: '+str(min_interactive))
	logger.info('ConfigFile: max_interactive: '+str(max_interactive))
	logger.info('ConfigFile: think_time: '+str(think_time))
	logger.info('ConfigFile: rampup_time: '+str(rampup_time))
	
def create_users():
	logger.info("START: Creating users for generating load")
	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(dbserver,22,username,password,look_for_keys=False)
	logging.getLogger("paramiko").setLevel(logging.INFO)
	for i in range(number_of_users):
		#client.exec_command("echo hello")
		logger.info('Creating user : '+'user'+str(i)+' ... ')
		time.sleep(0.1)
		client.exec_command('/usr/sbin/useradd user'+str(i))
		client.exec_command('/bin/echo user'+str(i)+':'+password+' | chpasswd')

	logger.info("END: Created users for generating load")
	client.close()

def copy_files():
	logger.info("START: Copying files to the remote server")
	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	logging.getLogger("paramiko").setLevel(logging.INFO)
	client.connect(dbserver,22,username,password,look_for_keys=False)
	sftp = client.open_sftp()

	#Copy the files to the remote server
	sftp.put("./iostat8","/tmp/iostat8")
	client.exec_command('/bin/chmod 755 /tmp/iostat8') 

	#Copy the dummy files. It is not required. Just for testing
	sftp.put("./script.sh","/tmp/script.sh")
	client.exec_command('/bin/chmod 755 /tmp/script.sh') 

	#sftp.put("./file1","/tmp/file1")
	#sftp.put("./file2","/tmp/file2")
	#sftp.put("./file3","/tmp/file3")
	#sftp.put("./file4","/tmp/file4")
	#sftp.put("./file5","/tmp/file5")
	#sftp.put("./file6","/tmp/file6")
	#sftp.put("./file7","/tmp/file7")
	#client.exec_command('/bin/chmod 755 /tmp/file*') 	

	logger.info("END: Copied files to the remote server")
	sftp.close()
	client.close()

def worker():
	
	#Get a random userid
	userid=random.randrange(1,number_of_users-1)
	username='user'+str(userid)

	#Get a random list of files
	count=len(file_list)
	nfiles=random.randrange(1,count)
	
	logger.debug('Number of Random files: '+str(nfiles)+' Total Count: '+str(count)+' Username'+str(username))
	logger.debug('File list: '+str(file_list))
	
	random_files=[]
	i=0
	while i<nfiles:
		index=random.randrange(0,count)
		if file_list[index] not in random_files:
			random_files.append(file_list[index])
		i=i+1

	logger.debug('Random Files: '+str(random_files))

	#Random time
	rtime=random.randrange(min_btime,max_btime)

	s=pxssh.pxssh()
	s.login(dbserver,username,password)
	s.sendline('/tmp/script.sh -t '+str(rtime)+' -f '+','.join(random_files))
	s.prompt()
	logger.debug(str(s.before))
	logger.info('/tmp/script.sh -t '+str(rtime)+' -f '+','.join(random_files))
	return

def main():
	if len(sys.argv) != 3:
		print("Error: Usage: ./driver -f load.conf")
		#ssys.exit(1)

	#Read the config file and initialize the program
	initialize(sys.argv[2])

	#Copy the binary and required files to remote server
	copy_files()

	#Create required users for generating load
	create_users()

	#Start ssh session for each user and make sure
	#that the number of session is maintained at
	#number_of_users

	active_threads=0
	while 1:

		logger.info("Active Threads: "+str(active_threads)+' '+'Active Users: '+str(active_users))
		if active_threads < active_users:
			logger.info("Inside: Active Threads: "+str(active_threads)+' '+'Active Users: '+str(active_users))
			t=threading.Thread(target=worker)
			t.start()
			time.sleep(rampup_time)

		active_threads=threading.active_count()
		logger.info("Active Threads: "+str(active_threads))

#End of main

#Program start from here ..!!
if __name__ == '__main__':
	main()
