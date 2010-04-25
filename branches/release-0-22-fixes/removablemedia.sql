
SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";




CREATE TABLE removablemedia (
  partitionuuid varchar(100) character set utf8 NOT NULL,
  freegb float NOT NULL,
  totalgb float NOT NULL,
  PRIMARY KEY  (partitionuuid)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;



CREATE TABLE removablemediavideos (
  partitionuuid varchar(100) NOT NULL,
  partitionlabel varchar(50) NOT NULL,
  fileinode int(11) NOT NULL,
  intid int(10) unsigned NOT NULL,
  title varchar(128) NOT NULL,
  subtitle text NOT NULL,
  director varchar(128) NOT NULL,
  plot text,
  rating varchar(128) NOT NULL,
  inetref varchar(255) NOT NULL,
  `year` int(10) unsigned NOT NULL,
  userrating float NOT NULL,
  length int(10) unsigned NOT NULL,
  season smallint(5) unsigned NOT NULL default '0',
  episode smallint(5) unsigned NOT NULL default '0',
  showlevel int(10) unsigned NOT NULL,
  filename text NOT NULL,
  coverfile text NOT NULL,
  childid int(11) NOT NULL default '-1',
  browse tinyint(1) NOT NULL default '1',
  watched tinyint(1) NOT NULL default '0',
  playcommand varchar(255) default NULL,
  category int(10) unsigned NOT NULL default '0',
  trailer text,
  host text NOT NULL,
  screenshot text,
  banner text,
  fanart text,
  insertdate timestamp NULL default CURRENT_TIMESTAMP,
  PRIMARY KEY  (partitionuuid,fileinode),
  KEY director (director),
  KEY title (title),
  KEY id_fs_uuid (partitionuuid),
  KEY partitionlabel (partitionlabel,title,subtitle(100))
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
