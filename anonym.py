#!/usr/bin/python3
# -*- coding: utf8 -*-
#
# Anonym - tool to anonymize captured customer data
#
# Author: Dmitriy Beryoza (0xd13a@gmail.com)
#
# Prerequisites:
#
# pip3 install faker
# pip3 install jsonpath-ng

import csv
import json 
import argparse
import os
import os.path
from faker import Faker
import jsonpath_ng
import jsonpath_ng.ext
import time
import ipaddress
import random
import traceback

VERSION = "1.04"
TOOL_NAME = f"Anonym {VERSION}" 

args = None          # Parsed command line arguments
handler_defs = []	 # Current handler definitions
current_line = -1    # Current line in the CSV file

fake = Faker()

def warning(msg, print_exception = False, field = None):
	""" Print warning message. """
	
	str = msg
	# If field spec is relevant, show it in the message
	if field != None:		
		if current_line > 1:
			# If we are dealing with a CSV print the line number
			str += " (field: %s, line: %d)" % (field, current_line)
		else:
			str += " (field: %s)" % (field)
	print(str)

	# Print exception trace if requested
	if print_exception and args.verbose:
		print(traceback.format_exc())

def error(msg, print_exception = False, field = None):
	""" Print error and quit. """
	warning(msg, print_exception, field)
	
	quit()

def find_nth(str, sub, n):
	""" Find n'th occurrence of the substring """
	start = str.find(sub)
	while start >= 0 and n > 1:
		start = str.find(sub, start+len(sub))
		n -= 1
	return start
	
class Field:
	""" Common supercalss for all field specifications """
	cache = {}

	def __init__(self, val):
		self.field_spec = val
	
		if args.type == 'csv':
			# Split the field spec into a name and path for CSV fields
			
			pos = val.find(".")
			
			if pos == -1:
				self.name = val
				self.path = None
			else:
				self.name = val[:pos]
				path = val[pos+1:]
				try:
					self.path = jsonpath_ng.ext.parse(path)
				except:
					error("Error parsing pattern: "+path, True)
					
		else:
			self.name = None
			try:
				self.path = jsonpath_ng.ext.parse(val)
			except:
				error("Error parsing pattern: "+val, True)
			
	def get_field_spec(self):
		""" Get original field specification """
		return self.field_spec
		
	def get_name(self):
		""" Get CSV column name """
		return self.name
		
	def anonymize_data(self, data):
		""" Anonymize a value (to be overridden in subclasses) """
		raise NotImplementedError('This method must be overridden in the subclass')

	def clean(self, data):
		""" Prepare data to be anonymized by stripping away junk """
		return data
		
	def anonymize(self, data):
		""" Anonymize data and cache values """
		data = self.clean(data)
		
		if data == None or data == "":
			return data
	
		if data in self.cache.keys():
			return self.cache[data]
		else:
			val = self.anonymize_data(data)
			self.cache[data] = val
			return val

	def is_json_field(self):
		""" Is it a JSON field? """
		return self.path != None

	def matches(self, val):
		""" Check if the path matches the JSON """
		return self.path.find(val)

			
class NameField(Field):
	""" Anonymize using 'FirstName LastName' """
	def anonymize_data(self, data):
		return fake.name()

class EmailField(Field):
	""" Anonymize e-mails """
	domains = {}
	
	def clean(self, data):
		""" Lowercase all e-mails """
		return str(data).lower()

	def anonymize_data(self, data):
		parts = data.split('@')
		if len(parts) > 1:
			# Fake domains and usernames separately, making sure specific domain always maps to the same fake domain
			if parts[1] in self.domains.keys():
				dom = self.domains[parts[1]]
			else:
				dom = fake.domain_name()
				self.domains[parts[1]] = dom
			return fake.email(domain = dom)
		else:	
			return fake.email(domain = "company.com")

class IDField(Field):
	""" Anonymize unique IDs """
	def anonymize_data(self, data):
		return fake.uuid4()

class HostField(Field):
	""" Anonymize host names """
	def anonymize_data(self, data):
		num_parts = data.count('.') + 1
		if num_parts == 1:
			return fake.hostname(0)
		else:
			return fake.domain_name(num_parts-1)

class IPField(Field):
	""" Anonymize IPs """
	
	networks = {}
	
	def clean(self, data):
		""" Clean IPs to remove port numbers and other unneeded info """
		if data.count('.') == 3:
			# IPv4
			data = data.split(":")[0]
		else:
			# IPv6
			data = data.split("%")[0]
			data = data.split("]")[0]
			if data.startswith("["):
				data = data[1:]
		return data
		
	def gen_new_ip(self, ip, delim, occurrence, fake_ip):
		""" Generate new IP, making sure IPs from the same network (/24 for IPv4, /64 for IPv6) map to the same fake network """
		pos = find_nth(ip, delim, occurrence)
		net = ip[:pos]
		host = ip[pos:]

		if net in self.networks.keys():
			new_net = self.networks[net]
		else:
			new_ip = fake_ip()
			new_net = new_ip[:find_nth(new_ip, delim, occurrence)]
			self.networks[net] = new_net
		return new_net + host	

	def anonymize_data(self, data):
		""" Anonymize IPs """
		if data.count(".") == 3:
			# IPv4

			# CIDR handling
			is_cidr = False
			if "/" in data:
				is_cidr = True
				data, netmask, *_ = data.split("/")
				try:
					val = int(netmask)
					if val < 0 or val > 32:
						is_cidr = False
				except ValueError:
					is_cidr = False
			try:
				ip = ipaddress.IPv4Address(data)
			except:
				warning("Error parsing IP: "+data, True, self.get_field_spec())
				return data

			new_ip = self.gen_new_ip(str(ip), ".", 3, lambda: fake.ipv4_public())
			if is_cidr:
				return str(ipaddress.IPv4Network(new_ip + "/" + netmask, strict=False))
			return new_ip
		else:
			# IPv6

			# CIDR handling
			is_cidr = False
			if "/" in data:
				is_cidr = True
				data, netmask, *_ = data.split("/")
				try:
					val = int(netmask)
					if val < 0 or val > 128:
						is_cidr = False
				except ValueError:
					is_cidr = False
			try:
				ip = ipaddress.IPv6Address(data).exploded
			except:
				warning("Error parsing IP: "+data, True, self.get_field_spec())
				return data

			new_ip = self.gen_new_ip(ip, ":", 4, lambda: ipaddress.IPv6Address(fake.ipv6()).exploded)
			if is_cidr:
				return str(ipaddress.IPv6Network(new_ip + "/" + netmask, strict=False))
			return new_ip

class CoordField(Field):

	def clean(self, data):
		""" Convert values to strings """
		self.type = str
		if isinstance(data, float):
			self.type = float
			return str(data)
		return data

	def anonymize_data(self, data):
		""" Anonymize coordinate """
		try:
			float_val = float(data)
		except:
			warning("Error parsing coordinate: "+data, True, self.get_field_spec())
			return data

		# We randomize with up to 0.5 degree difference (+/-50km)
		val = "%.3f" % (float_val + (random.randrange(1000) - 500) * 0.001)
		return self.type(val)

def parse_params():
	""" Parse parameters. """
	global args, handler_defs
	
	parser = argparse.ArgumentParser(description=TOOL_NAME+" - data anonymization tool")
	parser.add_argument("files", nargs='+', help="Names of the data file(s) to anonymize")
	
	parser.add_argument("-Fn", "--field-name",  help="Field containing personal names", type=str, action='append')
	parser.add_argument("-Fe", "--field-email", help="Field containing emails",         type=str, action='append')
	parser.add_argument("-Fu", "--field-id",    help="Field containing unique IDs",     type=str, action='append')
	parser.add_argument("-Fi", "--field-ip",    help="Field containing IPs",            type=str, action='append')
	parser.add_argument("-Fc", "--field-coord", help="Field containing coordinates",    type=str, action='append')
	parser.add_argument("-Fh", "--field-host",  help="Field containing host names",     type=str, action='append')
	parser.add_argument("-t",  "--type", help="Type of input files; valid values - 'csv' (default), 'json'", type=str, default='csv', choices=['csv', 'json'])
	parser.add_argument("-p",  "--predictable-names", help="Generate predictable artificial names (to use for regression testing)", action='store_true')
	parser.add_argument("-o",  "--output-folder", help="Output folder to use", type=str, required=True)
	parser.add_argument("-v",  "--verbose", help="Verbose output", action='store_true')

	args = parser.parse_args() 

	handler_defs.extend(process_field_param(args.field_name,  NameField))
	handler_defs.extend(process_field_param(args.field_email, EmailField))
	handler_defs.extend(process_field_param(args.field_id,    IDField))
	handler_defs.extend(process_field_param(args.field_ip,    IPField))
	handler_defs.extend(process_field_param(args.field_coord, CoordField))
	handler_defs.extend(process_field_param(args.field_host,  HostField))
	
	# Check output folder
	if not os.path.isdir(args.output_folder):
		error("Output folder does not exist: "+args.output_folder)
	
	# If requested (for testing), generate predictable fake values
	seed = 0
	if not args.predictable_names:
		seed = time.time()
	Faker.seed(seed)
	random.seed(seed)

def process_field_param(value, cls):
	""" Match field spec to a handler object """
	handler_defs = []
	if value != None:
		for f in value:
			handler_defs.append(cls(f))
	return handler_defs

def process_headers(row):
	""" Process header row """
	global handler_defs

	handlers = []
	unused_handlers = handler_defs[:]

	# Match handlers to columns
	for i in range(len(row)):
		handlers.append([])
		for handler in handler_defs:
			if row[i] == handler.get_name():
				handlers[i].append(handler)
				
				if handler in unused_handlers:
					unused_handlers.remove(handler)
	
	# Check if there are any columns missing and alert
	if len(unused_handlers) != 0:
		names = []
	
		for handler in unused_handlers:
			names.append(handler.get_name())
		
		warning("Referenced header(s) not found: " + str(names))
	
	return handlers
			
	
def anonymize_row(handlers, row):
	""" Anonymize individual CSV row """
	for i in range(len(row)):
		for h in handlers[i]:
			if h.is_json_field():
				# Anonymize JSON in a CSV cell 
				try:
					cell = json.loads(row[i])
					for match in h.matches(cell):
						cell = match.full_path.update(cell, h.anonymize(match.value))
					row[i] = json.dumps(cell)
				except:
					warning("Error parsing JSON: "+row[i], True, h.get_field_spec())
			else:
				row[i] = h.anonymize(row[i])
	return row

def process():
	global current_line
	
	# Process files one by one
	for file in args.files:
		print("Processing " + file)
		
		try:
			in_file = open(file, 'r') 
		except:
			error("Error opening input file: "+file, True)
		
		try:
			out_file_name = os.path.join(args.output_folder, os.path.basename(file))
			out_file = open(out_file_name, 'w')
		except:
			error("Error opening output file: "+out_file_name, True)
		
		try:
			# Process CSV
			if args.type == 'csv':
				csv_writer = csv.writer(out_file)
				csv_reader = csv.reader(in_file)
				headers = []
				current_line = 1
				for row in csv_reader:
					# Assume first row is a header row
					if current_line == 1:
						csv_writer.writerow(row)
						handlers = process_headers(row)
					else:		
						row = anonymize_row(handlers, row)
						csv_writer.writerow(row)
					
					current_line += 1
			# Process JSON
			else:
				try:
					data = json.load(in_file)
				except:
					error("Error parsing JSON file: "+file, True)
				for h in handler_defs:
					for match in h.matches(data):
						data = match.full_path.update(data, h.anonymize(match.value))
				out_file.write(json.dumps(data))
		
		# Exit without impediment when requested
		except SystemExit:
			pass
		except Exception as e:
			error("Error processing file:" + traceback.format_exc(), True)
		finally:
			out_file.close()
			in_file.close()
		
if __name__ == '__main__':
	
	parse_params()
	
	process()
