import sys
sys.path.append('../../scripts')

import os
import shutil
import time
from datetime import datetime
from timedprocess import Command
from Helper import generateResultsFromGraphUpdate
# from Helper import plotMean
import csv
import argparse
from sendEmail import EmailAlert

# graphs = [
# 	"144.mtx",  
# 	"333SP.mtx",
# 	"adaptive.mtx",
# 	"caidaRouterLevel.mtx",
# 	"coAuthorsCiteseer.mtx",
# 	"delaunay_n20.mtx",
# 	"fe_body.mtx",
# 	"hugetric-00000.mtx",
# 	"in2010.mtx",
# 	"luxembourg_osm.mtx",
# 	"rgg_n_2_20_s0.mtx",
# 	"sc2010.mtx",
# 	"vsp_mod2_pgp2_slptsk.mtx"
# ]

graphs = [
	#"liveJournal.mtx",
	#"cit-Patents.mtx",
	"orkut.mtx"
]

path = "data/"

def main():
	# Run all files from a directory
	print("##############################################################################")
	print("Callable as: python test_graph_update.py -h")
	print("##############################################################################")

	config_file = "config_update.json"
	testcases = {}
	if os.name == 'nt': # If on Windows
		build_path = os.path.join("build", "Release")
		sync_build_path = os.path.join("sync_build", "Release")
	else:
		build_path = "build/"
		sync_build_path = "build/"
	filetype = "pdf"
	time_out_val = 100
	generate_results = True

	parser = argparse.ArgumentParser(description='Test graph edge updates for various frameworks')
	parser.add_argument('-t', type=str, help='Specify which frameworks to test, separated by +, e.g. o+s+h+c+f+r+x ---> c : cuda | s : scatteralloc | h : halloc | o : ouroboros | f : fdgmalloc | r : register-efficient | x : xmalloc')
	parser.add_argument('-configfile', type=str, help='Specify the config file: config.json')
	parser.add_argument('-graphstats', action='store_true', default=False, help='Just write graph stats and do not run testcases')
	parser.add_argument('-runtest', action='store_true', default=False, help='Run testcases')
	parser.add_argument('-genres', action='store_true', default=False, help='Generate results')
	parser.add_argument('-genplot', action='store_true', default=False, help='Generate results file and plot')
	parser.add_argument('-timeout', type=int, help='Timeout Value in Seconds, process will be killed after as many seconds')
	parser.add_argument('-plotscale', type=str, help='log/linear')
	parser.add_argument('-filetype', type=str, help='png or pdf')
	parser.add_argument('-allocsize', type=int, help='How large is the manageable memory in GiB?', default=8)
	parser.add_argument('-device', type=int, help='Which device to use', default=0)
	parser.add_argument('-mailpass', type=str, help='Supply the mail password if you want to be notified', default=None)

	args = parser.parse_args()

	executable_extension = ""
	if os.name == 'nt': # If on Windows
		executable_extension = ".exe"
	# Parse approaches
	if(args.t):
		if any("c" in s for s in args.t):
			testcases["CUDA"] = os.path.join(build_path, str("c_graph_test") + executable_extension)
		if any("g" in s for s in args.t):
			testcases["Gallatin"] = os.path.join(build_path, str("b_graph_test") + executable_extension)
		if any("x" in s for s in args.t):
			testcases["XMalloc"] = os.path.join(sync_build_path, str("x_graph_test") + executable_extension)
		if any("h" in s for s in args.t):
			testcases["Halloc"] = os.path.join(sync_build_path, str("h_graph_test") + executable_extension)
		if any("s" in s for s in args.t):
			testcases["ScatterAlloc"] = os.path.join(sync_build_path, str("s_graph_test") + executable_extension)
		if any("o" in s for s in args.t):
			testcases["Ouroboros-P-S"] = os.path.join(build_path, str("o_graph_test_p") + executable_extension)
			testcases["Ouroboros-P-VA"] = os.path.join(build_path, str("o_graph_test_vap") + executable_extension)
			#really slow
			testcases["Ouroboros-P-VL"] = os.path.join(build_path, str("o_graph_test_vlp") + executable_extension)
			testcases["Ouroboros-C-S"] = os.path.join(build_path, str("o_graph_test_c") + executable_extension)
			testcases["Ouroboros-C-VA"] = os.path.join(build_path, str("o_graph_test_vac") + executable_extension)
			#C-VL is really slow, just wastes 10 minutes
			#testcases["Ouroboros-C-VL"] = os.path.join(build_path, str("o_graph_test_vlc") + executable_extension)
		if any("f" in s for s in args.t):
			testcases["FDGMalloc"] = os.path.join(sync_build_path, str("f_graph_test") + executable_extension)
		if any("r" in s for s in args.t):
			#testcases["RegEff-A"] = os.path.join(sync_build_path, str("r_graph_test_a") + executable_extension)
			testcases["RegEff-AW"] = os.path.join(sync_build_path, str("r_graph_test_aw") + executable_extension)
			# testcases["RegEff-C"] = os.path.join(sync_build_path, str("r_graph_test_c") + executable_extension)
			# testcases["RegEff-CF"] = os.path.join(sync_build_path, str("r_graph_test_cf") + executable_extension)
			# testcases["RegEff-CM"] = os.path.join(sync_build_path, str("r_graph_test_cm") + executable_extension)
			# testcases["RegEff-CFM"] = os.path.join(sync_build_path, str("r_graph_test_cfm") + executable_extension)
	
	# Run Testcases
	run_testcases = args.runtest
	
	# Generate results
	generate_results = args.genres

	# Generate plots
	generate_plots = args.genplot

	# Plot Axis scaling
	plotscale = args.plotscale

	# Config File
	if(args.configfile):
		config_file = args.configfile

	# Timeout (in seconds)
	if(args.timeout):
		time_out_val = args.timeout

	if(args.filetype):
		filetype = args.filetype

	ranged = ("range" in config_file)

	# Sort graphs for consistent ordering
	graphs.sort()

	mailalert = EmailAlert(args.mailpass)

	if not os.path.exists("results/aggregate"):
		os.mkdir("results/aggregate")
	
	if(args.graphstats):
		csv_path = "results/aggregate/graph_stats.csv"
		if(os.path.isfile(csv_path)):
			print("This file <" + csv_path + "> already exists, do you really want to OVERWRITE?")
			inputfromconsole = input()
			if not (inputfromconsole == "yes" or inputfromconsole == "y"):
				exit()
		with open(csv_path, "w", newline='') as csv_file:
			csv_file.write("Graph Stats, num vertices, num edges, mean adj length, std-dev, min adj length, max adj length\n")
		for graph in graphs:
			with open(csv_path, "a", newline='') as csv_file:
				csv_file.write(graph + ",")
			run_config = config_file + " " + path + graph + " " + str(1) + " " + csv_path
			executecommand = "{0} {1}".format(os.path.join(build_path, str("c_graph_exp_test") + executable_extension), run_config)
			print("#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#")
			print("Running command -> " + executecommand)
			print("#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#")
			print(executecommand)
			_, process_killed = Command(executecommand).run()
			if process_killed :
				Command("kill $(nvidia-smi | grep 'build' | awk '{ print $0 }' | xargs -n1 | head -5000 | head -5 | tail -1 | awk '{print $1}')").run(timeout=time_out_val)
				print("We killed the process!")
				with open(csv_path, "a", newline='') as csv_file:
					csv_file.write(",0,0,-------------------> Ran longer than " + str(time_out_val) + "\n")
			else:
				print("Success!")
				with open(csv_path, "a", newline='') as csv_file:
					csv_file.write("\n")
		exit()

	####################################################################################################
	####################################################################################################
	# Run testcases
	####################################################################################################
	####################################################################################################
	if run_testcases:
		for name, executable in testcases.items():
			suffix = ".csv"
			if "range" in config_file:
				suffix = "_range.csv"
			csv_path_insert = "results/graph_update_" + name + "_insert" + suffix
			csv_path_delete = "results/graph_update_" + name + "_delete" + suffix
			if(os.path.isfile(csv_path_insert)):
				print("This file <" + csv_path_insert + "> already exists, do you really want to OVERWRITE?")
				inputfromconsole = input()
				if not (inputfromconsole == "yes" or inputfromconsole == "y"):
					continue
			with open(csv_path_insert, "w", newline='') as csv_file:
				csv_file.write("Graph Update Testcase - " + name + ", mean(ms), std-dev(ms), min(ms), max(ms), median(ms), num iterations\n")
			with open(csv_path_delete, "w", newline='') as csv_file:
				csv_file.write("Graph Update Testcase - " + name + ", mean(ms), std-dev(ms), min(ms), max(ms), median(ms), num iterations\n")
			for graph in graphs:
				with open(csv_path_insert, "a", newline='') as csv_file:
					csv_file.write(graph + ",")
				with open(csv_path_delete, "a", newline='') as csv_file:
					csv_file.write(graph + ",")
				run_config = config_file + " " + path + graph + " " + str(0) + " init.csv " + csv_path_insert + " " + csv_path_delete + " " + str(args.allocsize) + " " + str(args.device)
				executecommand = "{0} {1}".format(executable, run_config)
				print("#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#")
				print("Running " + name + " with command -> " + executecommand)
				print("#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#")
				print(executecommand)
				_, process_killed = Command(executecommand).run(timeout=time_out_val)
				if process_killed :
					Command("kill $(nvidia-smi | grep 'build' | awk '{ print $0 }' | xargs -n1 | head -5000 | head -5 | tail -1 | awk '{print $1}')").run(timeout=time_out_val)
					print("We killed the process!")
					with open(csv_path_insert, "a", newline='') as csv_file:
						csv_file.write(",0,0,0,0,0,0,-------------------> Ran longer than " + str(time_out_val) + "\n")
					with open(csv_path_delete, "a", newline='') as csv_file:
						csv_file.write(",0,0,0,0,0,0,-------------------> Ran longer than " + str(time_out_val) + "\n")
				else:
					print("Success!")
					with open(csv_path_insert, "a", newline='') as csv_file:
						csv_file.write("\n")
					with open(csv_path_delete, "a", newline='') as csv_file:
						csv_file.write("\n")
				

			if args.mailpass:
				message = "Testcase {0} ran through! Testset: ({1})".format(str(name), " | ".join(testcases.keys()))
				mailalert.sendAlert(message)

	# ####################################################################################################
	# ####################################################################################################
	# # Generate new Results
	# ####################################################################################################
	# ####################################################################################################
	if generate_results:
		generateResultsFromGraphUpdate(testcases, "results", "Graphs", "update", 2, ranged)

	if args.mailpass:
		message = "Test Graph Update finished!"
		mailalert.sendAlert(message)

if __name__ == "__main__":
	main()