#!/bin/bash

# Usage:
#
#     ./import.sh username password
#
# Where 'username' and 'password' are your username and password for the
# Traveline National Dataset FTP server

if [[ ! -f manage.py ]] ; then
    echo './manage.py not found, exiting'
    exit 1
fi

# # create lockfile
# # I think it's important that this goes before the `trap`
# mkdir /var/lock/bustimes-import || {
#     echo "An import appears to be running already"
#     exit 1
# }

# function finish {
#     # remove lockfile
#     rmdir /var/lock/bustimes-import 2> /dev/null
# }
# trap finish EXIT SIGINT SIGTERM

USERNAME=$1
PASSWORD=$2


echo 'Starting import...'

# echo 'Importing NPTG'
# ./manage.py nptg_new

# echo 'Importing NaPTAN'
# ./manage.py naptan_new

# echo 'Importing Irish NaPTAN'
# ./manage.py naptan_new "Irish NaPTAN"


cd data/TNDS

echo 'Downloading NCSD and L files...'
ncsd_old=$(ls -l NCSD.zip)
wget -qN https://bodds-prod-coach-data.s3.eu-west-2.amazonaws.com/TxC-2.4.zip -O NCSD.zip
ncsd_new=$(ls -l NCSD.zip)

# tfl_old=$(ls -l L.zip)
# wget -qN https://tfl.gov.uk/tfl/syndication/feeds/journey-planner-timetables.zip -O L.zip
# tfl_new=$(ls -l L.zip)

cd ../..

if [[ $ncsd_old != $ncsd_new ]]; then
    echo 'NCSD.zip'
    ./manage.py import_transxchange data/TNDS/NCSD.zip
fi

# if [[ $tfl_old != $tfl_new ]]; then
#     echo 'L.zip'
#     ./manage.py import_transxchange data/TNDS/L.zip
# fi

echo 'Importing NOC'
./manage.py import_noc


if [[ $USERNAME == '' || $PASSWORD == '' ]]; then
   echo 'TNDS username and/or password not supplied :('
   exit 1
fi

echo 'Importing TNDS'
./manage.py import_tnds "$USERNAME" "$PASSWORD"

echo 'Importing GTFS'
./manage.py import_gtfs

echo 'Updating search indexes...'
./manage.py update_search_indexes

finish
