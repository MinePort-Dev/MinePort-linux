import os
import re
import stat
import subprocess
import sys
import tempfile
import minecraft-config
import wine


def updatePackages( packages ):
	"""
	Function to install or update package dependencies
	Ideally we would call some sort of system UI that users were familiar with to do this, but nothing that exists yet does what we need.
	"""

	packageList = " ".join( [ package.name for package in packages ] )

	# Create a temporary file to hold the installation completion status
	(fd, statusFile) = tempfile.mkstemp()
	os.close( fd )

	# Create a script to run, in a secure way
	(fd, scriptFile) = tempfile.mkstemp()
	script = """#!/bin/sh
check_sudo()
{
    # If your host file is misconfigured in certain circumstances this
    # can cause sudo to block for a while, which causes gksudo to go into
    # limbo and never return.
    timeout --signal=9 5 sudo -v -S </dev/null 2>/dev/null
    if [ $? -eq 124 -o $? -eq 137 ]; then
        # sudo timed out or was killed due to timeout
        cat <<__EOF__
sudo timed out, your hostname may be missing from /etc/hosts.

See https://support.steampowered.com/kb_article.php?ref=7493-ADXN-9620 for more details.
__EOF__
        return 1
    else
        return 0
    fi
}

cat <<__EOF__
Steam needs to install these additional packages:
	%s
__EOF__
check_sudo

# Check to make sure 64-bit systems can get 32-bit packages
if [ "$(dpkg --print-architecture)" = "amd64" ] && ! dpkg --print-foreign-architectures | grep i386 >/dev/null; then
    sudo dpkg --add-architecture i386
fi

# Update the package list, showing progress
sudo apt-get update | while read line; do echo -n "."; done
echo

# Install the packages!
sudo apt-get install %s
echo $? >%s
echo -n "Press return to continue: "
read line
""" % ( ", ".join( [ package.name for package in packages ] ), packageList, statusFile )
	os.write( fd, script.encode("utf-8") )
	os.close( fd )
	os.chmod( scriptFile, (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR) )

	try:
		subprocess.call( getTerminalCommandLine( "Package Install" ) + [scriptFile] )
	except KeyboardInterrupt:
		pass
	os.unlink( scriptFile )

	# Read the status out of the file, since if we ran the script in a
	# terminal the process status will be whether the terminal started
	try:
		status = int( open( statusFile ).read() )
	except ValueError:
		# The status wasn't written to the file
		status = 255

	os.unlink( statusFile )

	return status
