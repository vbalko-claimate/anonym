# Anonym - data anonymization tool 

## Overview

`anonym.py` replaces sensitive customer data with fake alternatives (built on [Faker library](https://faker.readthedocs.io/en/master/index.html)).

### Notable features:

* Works on CSV and JSON files
* Can anonymize portions of JSON documents embedded in CSV file cells (as seen in Azure and AWS logs)
* JSON fields are matched using [JSONPath](https://support.smartbear.com/alertsite/docs/monitors/api/endpoint/jsonpath.html) 
* Anonymizes people names, host names, IPs, coordinates, UIDs and e-mails (other types can be added if needed).
* Anonymized names are stable - all occurences of the same name are mapped to the same fake value
* Anonymizes e-mail names and domains separately, so that the domain is mapped to the same fake domain everywhere
* For IPs anonymizes network and host portions separately. The same network portion (/24 for IPv4, /64 for IPv6) maps to the same fake network
* Coordinates are anonymized within +/-50km range (to balance between the need for privacy and to make sure the new location is still in general vicintiy of the original)
* Can generate predictable fake names

## Installation

* Make sure you have Python 3 installed
* Install pre-requisites:

```
pip3 install -r requirements.txt
```

## Usage

### Available options:

```
usage: anonym.py [-h] [-Fn FIELD_NAME] [-Fe FIELD_EMAIL] [-Fu FIELD_ID]
                 [-Fi FIELD_IP] [-Fc FIELD_COORD] [-Fh FIELD_HOST]
                 [-t {csv,json}] [-p] -o OUTPUT_FOLDER [-v]
                 files [files ...]

Anonym 1.02 - data anonymization tool

positional arguments:
  files                 Names of the data file(s) to anonymize

optional arguments:
  -h, --help            show this help message and exit
  -Fn FIELD_NAME, --field-name FIELD_NAME
                        Field containing personal names
  -Fe FIELD_EMAIL, --field-email FIELD_EMAIL
                        Field containing emails
  -Fu FIELD_ID, --field-id FIELD_ID
                        Field containing unique IDs
  -Fi FIELD_IP, --field-ip FIELD_IP
                        Field containing IPs
  -Fc FIELD_COORD, --field-coord FIELD_COORD
                        Field containing coordinates
  -Fh FIELD_HOST, --field-host FIELD_HOST
                        Field containing host names
  -t {csv,json}, --type {csv,json}
                        Type of input files; valid values - 'csv' (default),
                        'json'
  -p, --predictable-names
                        Generate predictable artificial names (to use for
                        regression testing)
  -o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER
                        Output folder to use
  -v, --verbose         Verbose output
```

### How to specify fields:

* For CSV - use column name (e.g. `user`)
* For JSON inside CSV cells - use column name, dot, JSON path (e.g. `user.details.email`)
* For standalone JSON documents - use JSON path (e.g. `company[0].admin_email`)

### Examples:

| Anonymization use case | Command | Notes
| --- | --- | --- |
| People names | `python3 anonym.py -o output -Fn user data.csv`  |  |
| Unique IDs | `python3 anonym.py -o output -Fu uid data.csv`  |  |
| Host names | `python3 anonym.py -o output -Fh host data.csv`  |  |
| Coordinates | `python3 anonym.py -o output -Fc longitude -Fc latitude data.csv`  |  |
| IPs | `python3 anonym.py -o output -Fi ip data.csv`  |  |
| E-mails | `python3 anonym.py -o output -Fe username data.csv`  |  |
| Fields in JSON file | `python3 anonym.py -t json -o output -Fn userrec.name -Fe userrec.email data.json`  | Anonymizes name and email in the following JSON document:<b><br><br>{<br>&nbsp;&nbsp;"userrec":<br>&nbsp;&nbsp;&nbsp;&nbsp;{<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"name":"John Smith",<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"age":30,<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"email":"john.smith@company.com"<br>&nbsp;&nbsp;&nbsp;&nbsp;}<br>}</b> |
| JSON fields in CSV | `python3 anonym.py -o output -Fe details.email data.csv`  | Anonymizes e-mail in JSON cells in the following CSV:<b><br><br>user,details<br>john,"{""email"":""john@company.com"",""id"":123}"<br>mary,"{""email"":""mary@company.com"",""id"":456}"<br></b>|
| Complex JSON field example | `python3 anonym.py -o output -Fn user.$[?(@.type=="1")].data data.csv`  | Anonymizes only records of type `1` in the following CSV:<b><br><br>user<br>"[{""type"": ""1"", ""data"": ""John Smith""}, {""type"": ""2"", ""data"": ""u1234""}]"<br>"[{""type"": ""2"", ""data"": ""u5678""}, {""type"": ""1"", ""data"": ""Mary Johnson""}]"<br></b><br><br>For more examples of expressions see [JSONPath documentation](https://support.smartbear.com/alertsite/docs/monitors/api/endpoint/jsonpath.html) |

### Anonymizing common cloud logs:

**Azure (from Log Analytics)**

Signins log:

```
python3 anonym.py -o out -Fn userDisplayName_s -Fe userPrincipalName_s -Fc location_flat_s.geoCoordinates_latitude -Fc location_flat_s.geoCoordinates_longitude 
-Fc location_geoCoordinates_latitude_d -Fc location_geoCoordinates_longitude_d -Fh deviceDetail_flat_s.displayName -Fh deviceDetail_displayName_s 
-Fi IPAddress signins.csv 
```

AuditAzureActiveDirectory (AAAD) log:

```
python3 anonym.py -o out -Fe UserId_s -Fi ClientIP_s -Fi ActorIpAddress_s -Fe 'Actor_s.$[?(@.Type==5)].ID' aaad.csv 
```

Signins and AAAD logs together:

```
python3 anonym.py -o out -Fn userDisplayName_s -Fe userPrincipalName_s -Fc location_flat_s.geoCoordinates_latitude -Fc location_flat_s.geoCoordinates_longitude 
-Fc location_geoCoordinates_latitude_d -Fc location_geoCoordinates_longitude_d -Fh deviceDetail_flat_s.displayName -Fh deviceDetail_displayName_s 
-Fi IPAddress -Fe UserId_s -Fi ClientIP_s -Fi ActorIpAddress_s -Fe 'Actor_s.$[?(@.Type==5)].ID' signins.csv aaad.csv
```

## Testing

If you are making changes to the code base, make sure to:

* Execute the tests by running [tests.sh](test/tests.sh)
* Update the masters as necessary
* Add new tests if existing tests do not execute the changed functionality

## Change log

Version 1.01:

* Initial version

Version 1.02:

* Lowercase e-mails to make the fake versions more predictable

Version 1.03:

* More robust handling of domain names with multiple parts

Version 1.04:

* Better handling of IPs with CIDR components
* Making sure fake host name has as many parts as the original
* Minor bug fixes: correcting type handling, random seed
* Updating test masters to account for newline characters
* Added new unit tests for CIDR IPs and hostnames with different parts