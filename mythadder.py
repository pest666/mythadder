#!/usr/bin/python
# mythadder - automatically add video files on removable media to the mythvideo database upon connect/mount
# and remove them on disconnect.  Your distro should be set up to automount usb storage within 'mountWait' seconds after
# connection.
#
# requires udev and a rule like - SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", RUN+="/usr/bin/python /usr/bin/mythadder.py"
# to launch it - there's a .rules file in this archive you can use
#
# requires the python mysqldb library.  on ubuntu, apt-get install python python-mysqldb.
#

#
# configuration section
#

# add your video file extensions here
extensions = [".avi",".mkv",".ts",".m2ts",".mpg",".mp4"]

# to turn off logging, use False (no quotes) rather than this string
# this default assumes that /var/log/mythtv exists
logFile	= "/var/log/mythtv/mythadder" 

# seconds to wait for mount after udev event
mountWait  = 10 

#database config - CHANGE THIS TO REFLECT YOUR CONFIGURATION
dbHost	 = '192.168.1.1'
dbUser	 = 'mythtv'
dbPassword = 'supersecretpasswordofdoomseriouslyhuuuuurrrrrrr'
dbDatabase = 'mythconverg'

# Don't change anything below this unless you are a real python programmer and I've done something really dumb.
# This is my python 'hello world', so be gentle.

#
# code
#

import os
import commands
import re
import time
import MySQLdb
import statvfs

def doLog(logFile, output):
	if logFile:
		FILE = open(logFile,"a")
		FILE.writelines(output)

		FILE.close()

output = []
inodes = []

device = os.environ.get('DEVNAME',False)
action = os.environ.get('ACTION',False)
uuid   = os.environ.get('ID_FS_UUID',False)
label  = os.environ.get('ID_FS_LABEL',False)

doLog(logFile, '\n' + time.ctime() + '\n')

if device:
	doLog(logFile, action + ' ' + device + ' ' + label + ' ' + uuid + '\n')

	#
	# the drive is connected
	#
	if action == 'add':
		# connect to db
		try:		
			db = MySQLdb.connect(host = dbHost, user = dbUser, passwd = dbPassword, db = dbDatabase)
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		cursor = db.cursor()

		regex = re.compile(device)
		time.sleep(mountWait) # wait a few seconds until the drive is mounted
		mount_output = commands.getoutput('mount -v')
		for line in mount_output.split('\n'):
			if regex.match(line):
				mount_point = line.split(' type ')[0].split(' on ')[1]
				doLog(logFile, 'mounted at ' + mount_point + '\n')

		f = os.statvfs(mount_point)
		free_gb = f[statvfs.F_BAVAIL] * f[statvfs.F_FRSIZE] / float(1073741824)
		total_gb = f[statvfs.F_BLOCKS] * f[statvfs.F_FRSIZE] / float(1073741824)
		doLog(logFile, '%.2fGB free of %.2fGB total\n' % (free_gb, total_gb))

		# record partition uuid and free space
		sql = """
			INSERT INTO 
				removablemedia 
			SET partitionuuid = %s 
				,freegb = %s
				,totalgb = %s 
			ON DUPLICATE KEY UPDATE 
				freegb = %s
				,totalgb = %s;"""
		#doLog(logFile, sql  %  (uuid, free_gb, total_gb, free_gb, total_gb) + '\n')
		try:
			cursor.execute(sql, (uuid, free_gb, total_gb, free_gb, total_gb))
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		for directory in os.walk(mount_point):
			for file in directory[2]:
				for ext in extensions:
					if file.endswith(ext):
						thisFile = directory[0] + '/' + file
						thisBasename = os.path.basename(thisFile)
						thisInode = str(os.stat(thisFile).st_ino)

						output.append('found file at inode ' + thisInode + ':' + thisFile + '\n')

						inodes.append(thisInode)
						
						# insert each file that matches our extensions or update if it's already in the table
						sql = """
							INSERT INTO 
								removablemediavideos 
							SET partitionuuid = %s 
								,partitionlabel = %s 
								,fileinode = %s 
								,intid = 0 
								,title = %s 
								,subtitle = '' 
								,director = '' 
								,rating = '' 
								,inetref = '' 
								,year = 0 
								,userrating = 0.0 
								,showlevel = 1 
								,filename = %s 
								,coverfile = '' 
								,host = '' 
							ON DUPLICATE KEY UPDATE 
								partitionlabel = %s 
								,filename = %s;"""
						#doLog(logFile, sql  %  (uuid, label,  thisInode,  thisBasename,  thisFile,  label,  thisFile) + '\n')
						try:
							cursor.execute(sql, (uuid, label,  thisInode,  thisBasename,  thisFile,  label,  thisFile))
						except MySQLdb.Error, e:
							doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

						break
		inodeList = ','.join(inodes)
		#doLog(logFile, inodeList)
		
		# delete any rows for files that were deleted from the disk
		# there seems to be a bug in the mysql package that fails to handle the 
		# tuples for this query because of the inode list so we're letting python do the substitution here
		sql = """
			DELETE FROM 
				removablemediavideos 
			WHERE
				partitionuuid = '%s' AND
				fileinode NOT IN (%s) ;""" % (uuid,  inodeList)
		#doLog(logFile, sql  + '\n')
		try:
			cursor.execute(sql)
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		# insert anything from our table that already has an id from mythtv
		sql = """
			INSERT INTO videometadata (
				intid 
				,title
				,subtitle
				,director
				,plot
				,rating
				,inetref
				,year
				,userrating
				,length
				,season
				,episode
				,showlevel
				,filename
				,coverfile
				,childid
				,browse
				,watched
				,playcommand
				,category
				,trailer
				,host
				,screenshot
				,banner
				,fanart
				,insertdate)	
			SELECT
				intid 
				,title
				,subtitle
				,director
				,plot
				,rating
				,inetref
				,year
				,userrating
				,length
				,season
				,episode
				,showlevel
				,filename
				,coverfile
				,childid
				,browse
				,watched
				,playcommand
				,category
				,trailer
				,host
				,screenshot
				,banner
				,fanart
				,insertdate
			FROM
				removablemediavideos
			WHERE
				partitionuuid = %s AND
				intid != 0 ;""" 
		#doLog(logFile, sql % (uuid) + '\n')
		try:
			cursor.execute(sql, (uuid))
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		# get all our rows that have never been in mythtv before so we can insert them one at a time and capture the resulting mythtv id
		sql = """
			SELECT 				
				title
				,subtitle
				,director
				,plot
				,rating
				,inetref
				,year
				,userrating
				,length
				,season
				,episode
				,showlevel
				,filename
				,coverfile
				,childid
				,browse
				,watched
				,playcommand
				,category
				,trailer
				,host
				,screenshot
				,banner
				,fanart
				,insertdate
				,fileinode
			FROM 
				removablemediavideos 
			WHERE
				partitionuuid = %s AND
				intid = 0 ;""" 
		#doLog(logFile, sql % (uuid) + '\n')
		try:
			cursor.execute(sql,  (uuid))
			data = cursor.fetchall()
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		# insert one row from new videos and capture the id it gets assigned
		sql = """
			INSERT INTO videometadata (
				title
				,subtitle
				,director
				,plot
				,rating
				,inetref
				,year
				,userrating
				,length
				,season
				,episode
				,showlevel
				,filename
				,coverfile
				,childid
				,browse
				,watched
				,playcommand
				,category
				,trailer
				,host
				,screenshot
				,banner
				,fanart
				,insertdate)
			VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
			
			SELECT  LAST_INSERT_ID() AS intid;""" 
		#doLog(logFile, sql + '\n')
		for row in data :
			#doLog(logFile, row + '\n')
			try:
				# I can't believe it's 2010 and the basic mysql library for python doesn't put results into an associative array
				cursor.execute(sql, (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], row[23], row[24] ))
			except MySQLdb.Error, e:
				doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))
			cursor.nextset()
			intid = cursor.fetchone()[0]
			
			# update our table with the intid from mythtv so we can remove the rows when the drive is disconnected
			sql2 = """
				UPDATE removablemediavideos
				SET intid = %s
				WHERE partitionuuid = %s AND fileinode = %s
			"""
			try:
				cursor.execute(sql2, (intid,  uuid, row[25]))
			except MySQLdb.Error, e:
				doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

	#
	# the drive is being removed.
	#
	if action == 'remove':
		# connect to db
		try:		
			db = MySQLdb.connect(host = dbHost, user = dbUser, passwd = dbPassword, db = dbDatabase)
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		cursor = db.cursor()
		
		# update everything in our table to catch metadata changes done inside mythtv
		sql = """
			UPDATE 
				removablemediavideos rv,  videometadata vm
			SET
				rv.title = vm.title
				,rv.subtitle = vm.subtitle
				,rv.director = vm.director
				,rv.plot = vm.plot
				,rv.rating = vm.rating
				,rv.inetref = vm.inetref
				,rv.year = vm.year
				,rv.userrating = vm.userrating
				,rv.length = vm.length
				,rv.season = vm.season
				,rv.episode = vm.episode
				,rv.showlevel = vm.showlevel
				,rv.filename = vm.filename
				,rv.coverfile = vm.coverfile
				,rv.childid = vm.childid
				,rv.browse = vm.browse
				,rv.watched = vm.watched
				,rv.playcommand = vm.playcommand
				,rv.category = vm.category
				,rv.trailer = vm.trailer
				,rv.host = vm.host
				,rv.screenshot = vm.screenshot
				,rv.banner = vm.banner
				,rv.fanart = vm.fanart
			WHERE 
				rv.intid = vm.intid AND
				rv.partitionuuid = %s;"""
		try:
			cursor.execute(sql, (uuid))
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))

		# and finally delete all the rows in mythtv that match rows in our table for the drive being removed
		sql = """
			DELETE  
				vm
			FROM
				videometadata vm, removablemediavideos rv
			WHERE 
				rv.intid = vm.intid AND
				rv.partitionuuid = %s;"""
		try:
			cursor.execute(sql, (uuid))
		except MySQLdb.Error, e:
			doLog(logFile,  "Error %d: %s" % (e.args[0], e.args[1]))


doLog(logFile, output)

