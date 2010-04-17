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

# to turn off logging, use 'none'
loglevel = 'important,general'
logFile = '/var/log/mythtv/mythadder'

# seconds to wait for mount after udev event
mountWait  = 10 

# Don't change anything below this unless you are a real python programmer and I've done something really dumb.
# This is my python 'hello world', so be gentle.

MASCHEMA = 1001

#
# code
#

import os
import sys
import commands
import re
import time
from MythTV import MythDB, MythLog

LOG = MythLog(module='mythadder.py', lstr=logLevel)
if logFile:
    LOG.LOGFILE = open(logFile, 'a')

def prepTable(db):
    if db.settings.NULL['mythadder.DBSchemaVer'] is None:
        # create new table
        c = db.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS `z_removablevideos` (
              `partitionuuid` varchar(100) NOT NULL,
              `partitionlabel` varchar(50) NOT NULL,
              `fileinode` int(11) NOT NULL,
              `intid` int(10) unsigned NOT NULL,
              `title` varchar(128) NOT NULL,
              `subtitle` text NOT NULL,
              `director` varchar(128) NOT NULL,
              `plot` text,
              `rating` varchar(128) NOT NULL,
              `inetref` varchar(255) NOT NULL,
              `year` int(10) unsigned NOT NULL,
              `userrating` float NOT NULL,
              `length` int(10) unsigned NOT NULL,
              `season` smallint(5) unsigned NOT NULL default '0',
              `episode` smallint(5) unsigned NOT NULL default '0',
              `showlevel` int(10) unsigned NOT NULL,
              `filename` text NOT NULL,
              `coverfile` text NOT NULL,
              `childid` int(11) NOT NULL default '-1',
              `browse` tinyint(1) NOT NULL default '1',
              `watched` tinyint(1) NOT NULL default '0',
              `playcommand` varchar(255) default NULL,
              `category` int(10) unsigned NOT NULL default '0',
              `trailer` text,
              `host` text NOT NULL,
              `screenshot` text,
              `banner` text,
              `fanart` text,
              `insertdate` timestamp NULL default CURRENT_TIMESTAMP,
              PRIMARY KEY  (`partitionuuid`,`fileinode`),
              KEY `director` (`director`),
              KEY `title` (`title`),
              KEY `partitionuuid` (`partitionuuid`)
            ) ENGINE=MyISAM DEFAULT CHARSET=utf8;""")
        c.close()
        db.settings.NULL['mythadder.DBSchemaVer'] = MASCHEMA
    elif db.settings.NULL['mythadder.DBSchemaVer'] > MASCHEMA:
        # schema is too new, exit
        sys.exit(1)
    else:
        while db.settings.NULL['mythadder.DBSchemaVer'] < MASCHEMA:
            # if schema == some version
            # perform these tasks
            break

inodes = []

device = os.environ.get('DEVNAME',False)
action = os.environ.get('ACTION',False)
uuid   = os.environ.get('ID_FS_UUID',False)
label  = os.environ.get('ID_FS_LABEL',False)

if device:
    LOG(LOG.IMPORTANT, "%s %s" % (device, action), "%s at %s" % (label, uuid))

    #
    # the drive is connected
    #
    if action == 'add':
        # connect to db
        try:		
            db = MythDB()
            prepTable(db)
        except Exception, e:
            LOG(LOG.IMPORTANT, e.args[0])
            sys.exit(1)

        cursor = db.cursor()

        regex = re.compile(device)
        time.sleep(mountWait) # wait a few seconds until the drive is mounted
        mount_output = commands.getoutput('mount -v')
        for line in mount_output.split('\n'):
            if regex.match(line):
                mount_point = line.split(' type ')[0].split(' on ')[1]
                LOG(LOG.IMPORTANT, "Disk mounted at "+mountpoint)

        for directory in os.walk(mount_point):
            for file in directory[2]:
                if file.rsplit('.',1)[1] in extensions:
                    thisFile = directory[0] + '/' + file
                    thisBasename = os.path.basename(thisFile)
                    thisInode = str(os.stat(thisFile).st_ino)

                    LOG(LOG.IMPORTANT, "File found at inode "+thisInode, thisFile)
                    inodes.append(thisInode)
						
                    # insert each file that matches our extensions or update if it's already in the table
                    sql = """
                            INSERT INTO 
                                z_removablevideos 
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
                    try:
                        cursor.execute(sql, (uuid, label,  thisInode,  thisBasename,  thisFile,  label,  thisFile))
                    except Exception, e:
                        LOG(LOG.IMPORTANT, e.args[0])

        inodeList = ','.join(inodes)
		
        # delete any rows for files that were deleted from the disk
        # there seems to be a bug in the mysql package that fails to handle the 
        # tuples for this query because of the inode list so we're letting python do the substitution here
        sql = """
            DELETE FROM 
                z_removablevideos 
            WHERE
                partitionuuid = '%s' AND
                fileinode NOT IN (%s) ;""" % (uuid,  inodeList)
		
        try:
            cursor.execute(sql)
        except MySQLdb.Error, e:
            LOG(LOG.IMPORTANT, e.args[0])

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
                z_removablevideos
            WHERE
                partitionuuid = %s AND
                intid != 0 ;""" 
        try:
            cursor.execute(sql, (uuid))
        except Exception, e:
            LOG(LOG.IMPORTANT, e.args[0])

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
                z_removablevideos 
            WHERE
                partitionuuid = %s AND
                intid = 0 ;""" 

        try:
            cursor.execute(sql,  (uuid))
            data = cursor.fetchall()
        except Exception, e:
            LOG(LOG.IMPORTANT, e.args[0])

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
			
            SELECT LAST_INSERT_ID() AS intid;""" 
        for row in data:
            try:
                cursor.execute(sql, row)
            except Exception, e:
                LOG(LOG.IMPORTANT, e.args[0])
            cursor.nextset()
            intid = cursor.fetchone()[0]

            # update our table with the intid from mythtv so we can remove the rows when the drive is disconnected
            sql2 = """
                UPDATE z_removablevideos
                SET intid = %s
                WHERE partitionuuid = %s AND fileinode = %s
            """
            try:
                cursor.execute(sql2, (intid,  uuid, row[25]))
            except Exception, e:
                LOG(LOG.IMPORTANT, e.args[0])

    #
    # the drive is being removed.
    #
    if action == 'remove':
        # connect to db
        try:
            db = MythDB()
            prepTable(db)		
        except Exception, e:
            LOG(LOG.IMPORTANT, e.args[0]

        cursor = db.cursor()
		
        # update everything in our table to catch metadata changes done inside mythtv
        sql = """
            UPDATE 
                z_removablevideos rv,  videometadata vm
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
            cursor.execute(sql, uuid)
        except Exception, e:
            LOG(LOG.IMPORTANT, e.args[0])

        # and finally delete all the rows in mythtv that match rows in our table for the drive being removed
        sql = """
            DELETE  
                vm
            FROM
                videometadata vm, z_removablevideos rv
            WHERE 
                rv.intid = vm.intid AND
                rv.partitionuuid = %s;"""
        try:
            cursor.execute(sql, uuid)
        except MySQLdb.Error, e:
            LOG(LOG.IMPORTANT, e.args[0])



