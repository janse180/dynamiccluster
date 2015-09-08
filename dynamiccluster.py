#!/usr/bin/python

import getopt, sys, os
from dynamiccluster.server import DynamicServer
from dynamiccluster.__version__ import version
import os.path
import logging
from dynamiccluster.utilities import getLogger, get_log_level
from dynamiccluster.exceptions import NoClusterDefinedException
import traceback
import yaml

# Gets the instance of the logger.
log = getLogger("dynamiccluster")

class DynamicClusterLoader(object):
	def __init__(self):
		self.__server = None
		self.__argv = None
		self.__conf = dict()
		self.__conf["background"] = False
		self.__conf["pidfile"] = "/tmp/dynamiccluster.pid"
		self.__conf["verbose"] = 0
		self.__conf["configfile"] = "/etc/dynamiccluster/dynamiccluster.yaml"

	def displayVersion(self):
		print "Dynamic Cluster v" + version

	def displayUsage(self):
		""" Prints DynamicCluster command line options and exits
		"""
		print "Usage: "+self.__argv[0]+" [OPTIONS]"
		print
		print "Dynamic Cluster v" + version + " manages worker nodes in the cloud"
		print "based on the work load."
		print
		print "Options:"
		print "    -b                    start in background"
		print "    -f                    start in foreground"
		print "    -p <FILE>             pidfile path"
		print "    -c <FILE>             configuration file path"
		print "    -v, --verbose         change verbose level"
		print "    -h, --help            display this help message"
		print "    -V, --version         print the version"

	def __getCmdLineOptions(self, optList):
		""" Gets the command line options
		"""
		for opt in optList:
			if opt[0] == "-b":
				self.__conf["background"] = True
			if opt[0] == "-f":
				self.__conf["background"] = False
			if opt[0] == "-p":
				self.__conf["pidfile"] = opt[1]
			if opt[0] == "-c":
				self.__conf["configfile"] = opt[1]
			if opt[0] == "-v":
				self.__conf["verbose"] = self.__conf["verbose"] + 1
			if opt[0] == "-q":
				self.__conf["verbose"] = self.__conf["verbose"] - 1
			if opt[0] in ["-h", "--help"]:
				self.displayUsage()
				sys.exit(0)
			if opt[0] in ["-V", "--version"]:
				self.displayVersion()
				sys.exit(0)

	def bootstrap(self, argv):
		# Command line options
		self.__argv = argv

		# Reads the command line options.
		try:
			cmdOpts = 'bfp:c:hVvq'
			cmdLongOpts = ['help', 'version']
			optList, args = getopt.getopt(self.__argv[1:], cmdOpts, cmdLongOpts)
		except getopt.GetoptError:
			self.displayUsage()
			sys.exit(-1)

		self.__getCmdLineOptions(optList)
		verbose = self.__conf["verbose"]
		
		if not os.path.exists(self.__conf["configfile"]) or not os.path.isfile(self.__conf["configfile"]):
			print "Config file %s does not exist or is not a file." % self.__conf["configfile"]
			sys.exit(1)

		config=yaml.load(open(self.__conf["configfile"], 'r'))

		if 'logging' in config:
			if 'log_level' in config['logging']:
				log.setLevel(get_log_level(config['logging']['log_level']))
			if not self.__conf["background"]:
				# Add the default logging handler to dump to stderr
				logout = logging.StreamHandler(sys.stderr)
				# set a format which is simpler for console use
				formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s')
				# tell the handler to use this format
				logout.setFormatter(formatter)
				log.addHandler(logout)
			elif self.__conf["background"]:
				log_formatter = logging.Formatter(config['logging']['log_format'])
				file_handler = None
				if 'log_max_size' in config['logging']:
					file_handler = logging.handlers.RotatingFileHandler(
													config['logging']['log_location'],
													maxBytes=config['logging']['log_max_size'],
													backupCount=3)
				else:
					try:
						file_handler = logging.handlers.WatchedFileHandler(
													config['logging']['log_location'],)
					except AttributeError:
						# Python 2.5 doesn't support WatchedFileHandler
						file_handler = logging.handlers.RotatingFileHandler(
													config['logging']['log_location'],)
		
				file_handler.setFormatter(log_formatter)
				log.addHandler(file_handler)
		if verbose>0:
			log.setLevel(get_log_level(verbose))

		dynamic_cluster_server = DynamicServer(config, self.__conf["pidfile"], os.path.dirname(os.path.realpath(__file__)))
		try:
			dynamic_cluster_server.init()
		except NoClusterDefinedException:
			sys.stderr.write("You must define a valid cluster in config file.\n")
			#dynamic_cluster_server.quit()
			return False
		except Exception, e:
			#log.exception(e)
			print traceback.format_exc()
			#dynamic_cluster_server.quit()
			return False
		if self.__conf["background"]:
			dynamic_cluster_server.start()
		else:
			dynamic_cluster_server.run()
		return True

if __name__ == "__main__":
	loader = DynamicClusterLoader()
	if loader.bootstrap(sys.argv):
		sys.exit(0)
	else:
		sys.exit(-1)