#!/usr/bin/python

import getopt, sys, os
from dynamiccluster.server import Server
from dynamiccluster.__version__ import version
import os.path
import logging
from dynamiccluster.utilities import getLogger
from dynamiccluster.exceptions import NoClusterDefinedException
import traceback

# Gets the instance of the logger.
log = getLogger("dynamiccluster")

class DynamicClusterLoader(object):
	def __init__(self):
		self.__server = None
		self.__argv = None
		self.__conf = dict()
		self.__conf["background"] = False
		self.__conf["pidfile"] = "/var/run/dynamiccluster/server.pid"
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
		if not self.__conf["background"]:
			# Add the default logging handler to dump to stderr
			logout = logging.StreamHandler(sys.stderr)
			# set a format which is simpler for console use
			formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(threadName)s - %(message)s')
			# tell the handler to use this format
			logout.setFormatter(formatter)
			log.addHandler(logout)
		#print os.getcwd()
		if not os.path.isfile(self.__conf["configfile"]):
			sys.stderr.write("Configuration file %s does not exist.\n" % self.__conf["configfile"])
			return False
		dynamic_cluster_server = Server(self.__conf["pidfile"], self.__conf["configfile"], os.getcwd())
		try:
			dynamic_cluster_server.init(self.__conf["background"], verbose)
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