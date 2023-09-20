#!/bin/bash
#
# Tests for Anonym tool

OUT=./output
rm -rf $OUT
mkdir $OUT

# Run test and compare screen output to master
test() {
  echo "Testing: $1"
  python3 ../anonym.py $3 >$OUT/$2.out 2>&1
  diff ./master/$2.out $OUT/$2.out
}

# Run test and compare screen output to master, and output file to master output file
test_file() {
  test "$1" "$2" "$3"
  diff ./master/$4 $OUT/$4
}

# Check if file exists
check_not_exists() {
	if [ -e $1 ]; then echo "$1 exists, but should not!"; fi
}

# Run all tests
test      "No arguments"           "no_arguments"       ""
test      "Help"                   "help"               "-h"
test_file "Simple CSV"             "simple-csv"         "-p -o output -Fe email -Fn name -Fu id -Fi ip -Fh host -Fc long -Fc lat input/simple-csv.csv" "simple-csv.csv"
test_file "Simple CSV 2 files"     "simple-csv-2"       "-p -o output -Fe email -Fn name -Fu id -Fi ip -Fh host -Fc long -Fc lat input/simple-csv.csv input/simple-csv-2.csv" "simple-csv.csv"
diff ./master/simple-csv-2.csv $OUT/simple-csv-2.csv
test      "Bad pattern"            "bad-pattern"        "-o output -Fn json.' input/csv-json.csv"
test      "Bad pattern verbose"    "bad-pattern-verb"   "-v -o output -Fn json.' input/csv-json.csv"
test      "Header not found"       "header-not-found"   "-o output -Fn badname1 -Fh badname2 input/csv-json.csv"
test_file "CSV with JSON"          "csv-json"           "-p -o output -t csv -Fe json.a -Fu json.b -Fn json2.\$[?(@.a==\"1\")].b -Fh json2.\$[?(@.a==\"2\")].b input/csv-json.csv" "csv-json.csv"
test_file "Simple JSON"            "simple-json"        "-p -o output -t json -Fn a.b -Fu x -Fh \$.array[?(@.a==\"1\")].b input/simple-json.json" "simple-json.json"
test      "Bad coord"              "bad-coord"          "-o output -Fc test input/bad-coord.csv"
test      "Bad embedded JSON"      "bad-embed-json"     "-o output -Fu test.a input/bad-embed-json.csv"
test      "Bad IPv4"               "bad-ipv4"           "-o output -Fi test input/bad-ipv4.csv"
test      "Bad IPv6"               "bad-ipv6"           "-o output -Fi test input/bad-ipv6.csv"
test      "Bad JSON file"          "bad-json-file"      "-o output -t json -Fi test input/bad-json.json"
test      "Missing input file"     "missing-input-file" "-o output -Fi test input/missing.csv"
test      "Missing output folder"  "missing-out-folder" "-o missing -Fi test input/simple-csv.csv"
test_file "Dirty IPs"              "dirty-ips"          "-p -o output -Fi ip input/dirty-ips.csv" "dirty-ips.csv"
test_file "CIDR IPs"               "cidr-ips"           "-p -o output -Fi test input/cidr-ips.csv" "cidr-ips.csv"
test_file "Host names"             "host-names"         "-p -o output -Fh test input/host-names.csv" "host-names.csv"


