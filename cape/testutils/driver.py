#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
:mod:`cape.testutils.driver`: CAPE's main test case driver
===========================================================

This module contains the underlying functions that operate the CAPE
test driver for individual tests.


The test crawler is initiated using the command:

    .. code-block:: console

        $ cape_TestCase.py

This calls the :func:`cli` command from this module.

Options are processed using the :mod:`cape.testutils.crawleropts`
module, which looks for the ``cape-test.json`` file to process any
options to the test crawler.

:See Also:
    * :mod:`cape.testutils.testopts`
    * :mod:`cape.testutils.crawleropts`
"""

# Standard library modules
import io
import os
import time
import shlex
import shutil
import sys

# Local modules
from . import argread
from . import fileutils
from . import testshell
from . import testopts
from . import verutils


# Create tuples of types
if verutils.ver > 2:
    # Categories of types for Python 3
    strlike = str
    intlike = int
    filelike = io.IOBase
    # Create extra handle for unicode objects
    unicode = str
else:
    # Categories of types for Python 2
    strlike = (str, unicode)
    intlike = (int, long)
    filelike = (file, io.IOBase)

# Third-party modules
np = None
plt = None


# CLI help message
HELP_TESTCASE = r"""
CAPE single-case test driver
=============================

The test driver executes a test in the current folder.  This consists
of several steps that run the test in a subfolder (which is called
work/ by default).  If that subfolder exists, it is deleted at the
beginning of the test.

:Usage:

    .. code-block:: console
        
        $ cape_TestCase.py [OPTIONS]

:Options:
    -f, --json FNAME
        Read settings from file *FNAME* {cape-test.json}

:Versions:
    * 2019-07-06 ``@ddalle``: Version 1.0
"""


# Function to import Matplotlib
def _import_pyplot():
    # Make global variables
    global np
    global plt
    # Exit if plt imported
    if plt is not None:
        return
    # Import the module
    try:
        # Import matplotlib first to set backend
        import matplotlib
        # Turn off interactive windows
        matplotlib.use("Agg")
        # Import pyplot
        import matplotlib.pyplot as plt
        # Import NumPy
        import numpy as np
    except ImportError:
        return


# String container
class ResultsStream(object):
    r"""Simple string extension with :func:`write` interface

    :Call:
        >>> fp = ResultsStream()
        >>> fp = ResultsStream(txt)
    :Inputs:
        *txt*: {``None``} | :class:`str`
            Initial text
    :Outputs:
        *fp*: :class:`ResultsStream`
            String with :func:`write` interface
        *fp.txt*: :class:`str`
            Current contents of the stream
    :Versions:
        * 2021-10-12 ``@ddalle``: Version 1.0
    """
    def __init__(self, txt=None):
        if txt is None:
            self.txt = ""
        else:
            self.txt = txt

    def __repr__(self):
        return repr(self.txt)

    def __str__(self):
        return self.txt.__str__()

    def write(self, txt):
        r"""Append to stream's text by adding it to the end

        :Call:
            >>> fp.write(txt)
        :Inputs:
            *fp*: :class:`ResultsStream`
                String with :func:`write` 
            *txt*: :class:`str`
                Additional text
        :Versions:
            * 2021-10-12 ``@ddalle``: Version 1.0
        """
        self.txt += txt

    def prepend(self, txt):
        r"""Append to stream's text by adding it to the beginning

        :Call:
            >>> fp.prepend(txt)
        :Inputs:
            *fp*: :class:`ResultsStream`
                String with :func:`write` 
            *txt*: :class:`str`
                Additional text
        :Versions:
            * 2021-10-12 ``@ddalle``: Version 1.0
        """
        self.txt = txt + self.txt


# Crawler class
class TestDriver(object):
    r"""Test driver class

    :Call:
        >>> driver = TestDriver(**kw)
    :Inputs:
        *f*, *json*: {``"cape-test.json"``} | :class:`str`
            Name of JSON settings file
    :Outputs:
        *testd*: :class:`cape.testutils.testd.TestDriver`
            Test driver controller
    :Versions:
        * 2019-07-03 ``@ddalle``: Started
    """
    # Initialization method
    def __init__(self, *a, **kw):
        r"""Initialization method

        :Versions:
            * 2019-07-03 ``@ddalle``: Version 1.0
        """
        # Process options file name
        fname = kw.pop("f", kw.pop("json", "cape-test.json"))
        # Save name of file
        self.fname = os.path.split(fname)[1]
        # Save current directory
        self.RootDir = os.getcwd()
        # Save directory name
        self.dirname = os.path.split(self.RootDir)[1]
        # Process options
        self.opts = testopts.TestOpts(fname)
        # Get commands to run
        cmds = self.opts.get_commands()
        # Standard attributes
        self.fdoc = None
        self.frst = None
        # Container for texts
        self.TestSummary_List = []
        # Results attributes
        self.TestStatus = True
        self.TestStatus_List = []
        self.TestStatus_ReturnCode = True
        self.TestStatus_MaxTime = True
        self.TestStatus_STDOUT = True
        self.TestStatus_STDERR = True
        self.TestStatus_PNG = True
        self.TestStatus_File = True
        self.TestRunTimeTotal = 0.0
        self.TestRunTimeList = []
        self.TestReturnCodes = []
        self.TestCommandsNum = 0
        self.TestCommandsRun = 0
        # Save number of intended commands
        self.TestCommandsNum = len(cmds)

    # String method
    def __str__(self):
        r"""String method

        :Versions:
            * 2019-07-09 ``@ddalle``: <TestDriver('$dirname', n=$ncommands)>
        """
        return "<%s('%s', n=%i)>" % (
            self.__class__.__name__,
            self.dirname,
            len(self.opts.get_commands()))

    # Representation method
    def __repr__(self):
        r"""Representation method

        :Versions:
            * 2019-07-09 ``@ddalle``: <TestDriver('$dirname', n=$ncommands)>
        """
        return "<%s('%s', n=%i)>" % (
            self.__class__.__name__,
            self.dirname,
            len(self.opts.get_commands()))

    # Reset results for test
    def init_test_results(self):
        r"""(Re)initialize attributes that store results of test

        :Call:
            >>> testd.init_test_results()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Versions:
            * 2019-07-07 ``@ddalle``: Version 1.0
        """
        # Reset test results attributes
        self.TestStatus = True
        # Reasons for failure
        self.TestStatus_ReturnCode = []
        self.TestStatus_MaxTime = []
        self.TestStatus_STDOUT = []
        self.TestStatus_STDERR = []
        self.TestStatus_PNG = []
        self.TestStatus_File = []
        # Statistics
        self.TestRunTimeTotal = 0.0
        self.TestRunTimeList = []
        self.TestReturnCodes = []
        self.TestCommandsNum = 0
        self.TestCommandsRun = 0

    # Run the main test
    def run(self):
        r"""Execute the test controlled by the driver

        :Call:
            >>> results = testd.run()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Outputs:
            *results*: :class:`dict`
                Results from :func:`get_results_dict`
        :Versions:
            * 2019-07-05 ``@ddalle``: Version 1.0
        """
        # Go to home folder
        fpwd = os.getcwd()
        os.chdir(self.RootDir)
        # Open rst file and process folder
        self.init_rst()
        # Prepare files (also enters working folder)
        self.prepare_files()
        # Run any commands
        results = self.exec_commands()
        # Write all results
        self.write_results()
        # Return to original location
        os.chdir(fpwd)
        # Output
        return results

    # Write reST results all at once
    def write_results(self):
        r"""Write ``.rst`` file of results

        :Call:
            >>> testd.write_results()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Versions:
            * 2021-10-12``@ddalle``: Version 1.0
        """
        # Get *rst* file handle
        frst = self.frst
        # Check if it's open
        if not isinstance(frst, filelike) or frst.closed:
            return
        # Begin documentation
        self.write_rst_intro()
        # Loop through commands
        for i in range(self.TestCommandsRun):
            # Get handle for results of command *i*
            fp = self.get_results_summary(i)
            # Write it to .rst file
            frst.write(fp.txt)
        # Close rst file
        self.close_rst()

    # Prepare a test
    def prepare_files(self):
        r"""Prepare test folder for execution

        :Call:
            >>> testd.prepare_files()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Attributes:
            *testd.frst*: ``None`` | :class:`file`
                File handle to new ReST file if applicable
        :Versions:
            * 2019-07-03 ``@ddalle``: Version 1.0
        """
        # Name of container folder
        fwork = self.opts.get("ContainerName", "work")
        # Delete contents if present
        if os.path.isdir(fwork):
            shutil.rmtree(fwork)
        # Create folder
        os.mkdir(fwork)
        # Get files to copy/link
        fcopy = self.opts.get("CopyFiles", [])
        flink = self.opts.get("LinkFiles", [])
        dcopy = self.opts.get("CopyDirs", [])
        dlink = self.opts.get("LinkDirs", [])
        # Copy files
        for fname in fileutils.expand_file_list(fcopy, typ="f"):
            # Double-check for file
            if not os.path.isfile(fname):
                continue
            # Copy it
            shutil.copy(fname, os.path.join(fwork, fname))
        # Link files
        for fname in fileutils.expand_file_list(flink, typ="f"):
            # Double-check for file
            if not os.path.isfile(fname):
                continue
            # Link it
            os.symlink(fname, os.path.join(fwork, fname))
        # Copy dirs
        for fname in fileutils.expand_file_list(dcopy, typ="d"):
            # Double-check for dir
            if not os.path.isdir(fname):
                continue
            # Copy folder and its contents
            shutil.copytree(fname, os.path.join(fwork, fname))
        # Link dirs
        for fname in fileutils.expand_file_list(dlink, typ="d"):
            # Double-check for dir
            if not os.path.isdir(fname):
                continue
            # Create link to folder and its contents
            os.symlink(fname, os.path.join(fwork, fname))
        # Enter the folder
        os.chdir(fwork)

    # Start log file
    def init_rst(self):
        r"""Initialize ReST file of test results

        :Call:
            >>> testd.init_rst()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Attributes:
            *testd.frst*: ``None`` | :class:`file`
                Open or newly opened file handle if applicable
        :Versions:
            * 2019-07-09 ``@ddalle``: Version 1.0
        """
        # If *frst* is already a file, do nothing
        if isinstance(self.frst, filelike):
            return
        # Get option for root level
        nroot = self.opts.get("RootLevel")
        # Relative path to test documentation from "root"
        fdoc_rel = self.opts.get("DocFolder")
        # Check these options
        if nroot is None:
            # No root level
            self.close_rst()
            return
        elif fdoc_rel is None:
            # No documentation folder
            self.close_rst()
            return
        elif not isinstance(nroot, int):
            # Bad type for root level
            raise TypeError(
                "'RootLevel' option must be int (got '%s')"
                % froot.__class__.__name__)
        elif nroot > 0:
            # Bad root level
            raise ValueError(
                "'RootLevel' option must be <= 0 (got %i)" % nroot)
        elif not isinstance(fdoc_rel, strlike):
            # Bad type for doc folder
            raise TypeError(
                "'DocFolder' option must be str (got '%s')"
                % fdoc_rel.__class__.__name__)
        # Initialize root folder for documentation
        fdoc = self.RootDir
        # Go up *nroot* levels
        for i in range(-nroot):
            # Raise one level
            fdoc = os.path.dirname(fdoc)
        # Remember current location
        fpwd = os.getcwd()
        # Catch errors during folder generation
        try:
            # Change to documentation root folder
            os.chdir(fdoc)
            # List of subdirectories, last one copies test folder name
            docdirs = fdoc_rel.split("/") + [self.dirname]
            # Create folders as needed
            for fdir in docdirs:
                # Check if folder exists
                if not os.path.isdir(fdir):
                    # Otherwise, create it
                    os.mkdir(fdir)
                # Enter it
                os.chdir(fdir)
                # Join to doc folder
                fdoc = os.path.join(fdoc, fdir)
            # Return to original location
            os.chdir(fpwd)
        except Exception:
            # Return to original location
            os.chdir(fpwd)
            # Fail
            raise SystemError(
                "Failed to create folder '%s' in '%s'" % (fdir, fdoc))
        # Save documentation folder
        self.fdoc = fdoc
        # Total path
        fname = os.path.join(fdoc, "index.rst")
        # Open the file
        self.frst = open(fname, "w")

    # Write header for ReST file
    def write_rst_intro(self):
        r"""Write intro section for ReST log file

        :Call:
            >>> testd.write_rst_intro()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Attributes:
            *testd.frst*: ``None`` | :class:`file`
                File handle to which intro is written, if applicable
        :Versions:
            * 2019-07-09 ``@ddalle``: Version 1.0
            * 2021-10-12 ``@ddalle``: Version 2.0; result in title
        """
        # Check if file is actually open
        if self.frst is None:
            return
        # Get title
        ttl = self.opts.get("DocTitle")
        # Default title
        if ttl is None:
            # Use the folder name
            ttl = "Test ``%s``: " % self.dirname
        # Add status
        if self.TestStatus:
            # Passed all tests
            ttl += "PASS"
        else:
            # Failed at least one command
            ttl += "**FAIL** (command %i)" % self.TestCommandsRun
        # Get the current time
        t = time.localtime()
        # Get timezone name using DST flag
        if t.tm_isdst:
            # Daylight savings timezone name
            tz = time.tzname[1]
        else:
            # Standard timezone name
            tz = time.tzname[0]
        # Get option for root level
        nroot = self.opts.get("RootLevel")
        # Get path to root
        if nroot is not None and nroot < 0:
            # Initialize root folder for documentation
            fdoc = self.RootDir
            # Go up *nroot* levels
            for i in range(-nroot):
                # Raise one level
                fdoc = os.path.dirname(fdoc)
            # Document path relative to root
            froot = os.path.relpath(self.RootDir, fdoc)
        else:
            # Just use full path to test
            froot = self.RootDir
        # Create an indent
        tab = "    "
        # Get handle to save some characters
        f = self.frst
        # Write a header comment
        f.write("\n")
        f.write(".. This documentation written by TestDriver()\n")
        f.write("   on ")
        f.write("%04i-%02i-%02i " % (t.tm_year, t.tm_mon, t.tm_mday))
        f.write("at %02i:%02i %s" % (t.tm_hour, t.tm_min, tz))
        f.write("\n\n")
        # Write title
        f.write(ttl + "\n")
        f.write("=" * (len(ttl) + 2))
        f.write("\n\n")
        # Indentation
        tab = "    "
        # Check for intro written beforehand
        fintro = self.opts.get("DocFileIntro")
        # Check if it's a file name and exists
        if fintro is None:
            # Do nothing
            pass
        elif not isinstance(fintro, strlike):
            # Invalid type
            raise TypeError(
                "'DocFileIntro' must be a string (got '%s')"
                % fintro.__class__.__name__)
        else:
            # Absolute path
            if not os.path.isabs(fintro):
                # Relative to test folder, not working folder
                fintro = os.path.join(self.RootDir, fintro)
            # Check if file exists
            if not os.path.isfile(fintro):
                raise SystemError("DocFileIntro '%s' does not exist" % fintro)
            # Otherwise, copy the file
            f.write(open(fintro).read())
            # Add a blank line for good measure
            f.write("\n")
        # Summary: status and date
        if self.TestStatus:
            # Note the success
            f.write("This test PASSED ")
        else:
            # Note the failure and which command failed
            f.write(
                "This test **FAILED** (command %i) " % self.TestCommandsRun)
        # Write the date
        f.write("on %04i-%02i-%02i " % (t.tm_year, t.tm_mon, t.tm_mday))
        f.write("at %02i:%02i %s\n\n" % (t.tm_hour, t.tm_min, tz))
        # Summary: location
        f.write("This test is run in the folder:\n\n")
        f.write("    ``%s%s``\n\n" % (froot, os.sep))
        # Summary: container
        fwork = self.opts.get("ContainerName", "work")
        f.write("and the working folder for the test is\n\n")
        f.write("    ``%s%s``\n\n" % (fwork, os.sep))
        # Summary: commands
        f.write("The commands executed by this test are\n\n")
        f.write(tab + ".. code-block:: console\n\n")
        # Loop through commands
        for cmd in self.opts.get_commands():
            f.write(2*tab + "$ " + cmd + "\n")
        # Blank line
        f.write("\n")
        # Check for files to print in folder
        fshow_list = self.opts.get("DocFilesShow", [])
        fshow_list = testopts.enlist(fshow_list)
        # Loop through files
        for (i, fshow) in enumerate(fshow_list):
            # Absolute path
            if not os.path.isabs(fshow):
                fshow = os.path.join(self.RootDir, fshow)
            # # Check if file exists
            if not os.path.isfile(fshow):
                raise SystemError("DocFilesShow '%s' does not exist" % fshow)
            # Get lexer
            lang = self.opts.getel("DocFilesLexer", i, vdef="none")
            # Split into parts
            fdir, fname = os.path.split(fshow)
            # Create a header
            f.write("**Included file:** ``%s``\n\n" % fname)
            # Start a code block
            f.write(tab + (".. code-block:: %s\n\n" % lang))
            # Insert contents
            for line in open(fshow).readlines():
                # Write it
                f.write(tab + tab + line)
            # Check for that stupid modern convention that the last
            # line doesn't end with a newline
            if not line.endswith("\n"):
                # End the damn line
                f.write("\n")
            # Blank line
            f.write("\n")
        # Check for files to link
        flink_list = self.opts.get("DocFilesLink", [])
        flink_list = testopts.enlist(flink_list)
        # Create header if appropriate
        if len(flink_list) > 0:
            # Start bullet list
            f.write(":Included Files:\n")
        # Loop through files
        for flink in flink_list:
            # Absolute path
            if not os.path.isabs(flink):
                flink = os.path.join(self.RootDir, flink)
            # # Check if file exists
            if not os.path.isfile(flink):
                raise SystemError("DocFilesLink '%s' does not exist" % flink)
            # Split into parts
            fdir, fname = os.path.split(flink)
            # Copy the file
            shutil.copy(flink, os.path.join(self.fdoc, fname))
            # Create link
            f.write("    * :download:`%s`\n" % fname)
        # Blank line after download list
        if len(flink_list) > 0:
            # Start bullet list
            f.write("\n")
        # Ensure everything has been written
        f.flush()

    # Close ReST file
    def close_rst(self):
        r"""Close ReST log file, if open

        :Call:
            >>> testd.close_rst()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Attributes:
            *testd.frst*: ``None`` | :class:`file`
                Closed file handle if applicable
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Check if *frst* is a file
        if isinstance(self.frst, filelike):
            # Close it
            self.frst.close()
            # Delete handle
            self.frst = None

    # Execute test
    def exec_commands(self):
        r"""Execute tests in the current folder

        :Call:
            >>> results = testd.exec_commands()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Outputs:
            *results*: :class:`dict`
                Results from :func:`get_results_dict`
        :Versions:
            * 2019-07-05 ``@ddalle``: Version 1.0
        """
        # Get commands to run
        cmds = self.opts.get_commands()
        # Initialize test results
        self.init_test_results()
        # Save number of commands
        self.TestCommandsNum = len(cmds)
        # Loop through commands
        for i, cmd in enumerate(cmds):
            # Get subtitle
            subt = self.opts.getel("CommandTitles", i, vdef=None)
            # Status update message
            msg = (
                "    Testing command %i/%i" % (i+1, self.TestCommandsNum))
            # Include title
            if subt:
                msg += ": %s" % subt
            # Status update
            sys.stdout.write(msg)
            sys.stdout.flush()
            # Break command into parts
            cmdi = shlex.split(cmd)
            # Get handles
            fnout, fout = self.opts.get_STDOUT(i)
            fnerr, ferr = self.opts.get_STDERR(i, fout)
            # Maximum allowed time
            tmax = self.opts.getel("MaxTime", i, vdef=None)
            tstp = self.opts.getel("MaxTimeCheckInterval", i, vdef=None)
            # Convert maximum time to seconds
            tsec = testshell._time2sec(tmax)
            # Total time is cumulative
            if tsec:
                # Subtract any existing time from previous commands
                tsec = tsec - self.TestRunTimeTotal
            # Call the command
            t, ierr, out, err = testshell.comm(
                cmdi, maxtime=tsec, dt=tstp, stdout=fout, stderr=ferr)
            # Close files
            if isinstance(fout, filelike):
                fout.close()
            # (No concern about closing same file twice if STDERR==STDOUT)
            if isinstance(ferr, filelike):
                ferr.close()
            # Start the log for this command
            self.write_command_summary(i, cmd)
            # Check the return code
            self.process_results_returncode(i, ierr)
            # Check for timeout and update timers
            self.process_results_maxtime(i, t)
            # Check STDOUT and STDERR against targets
            self.process_results_stdout(i, fnout)
            self.process_results_stderr(i, fnerr, fnout)
            # Check images
            self.process_results_png(i)
            # Check files
            self.process_results_file(i)
            # Update number of commands run
            self.TestCommandsRun = i + 1
            # Create handle for test status list
            self._extend_attribute_list("TestStatus_List", i)
            # Save status
            self.TestStatus_List[i] = self.TestStatus
            # Write title
            self.write_command_title(i)
            # Exit if a failure was detected
            if self.TestStatus:
                # Clean up STDOUT
                sys.stdout.write("\r")
                sys.stdout.write(" " * len(msg))
                sys.stdout.write("\r")
                sys.stdout.flush()
            else:
                # Remember failur
                sys.stdout.write(" FAILED\n")
                # Exit test
                break
        # Output
        return self.get_results_dict()

    # Get or create results handler
    def get_results_summary(self, i):
        r"""Get or create results summary for command *i*

        :Call:
            >>> fp = testd.get_results_summary(i)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
        :Outputs:
            *fp*: :class:`ResultsStream`
                String-like object with :func:`write` interface
        :Versions:
            * 2021-10-12 ``@ddalle``: Version 1.0
        """
        # Get current list of results text handlers
        fps = self.TestSummary_List
        # Check if already present
        if i < len(fps):
            # Use it
            return fps[i]
        # Append as many as needed
        for j in range(len(fps), i+1):
            fps.append(ResultsStream())
        # Return the last one
        return fps[i]

    # Ensure an attribute has at least *i* entries
    def _extend_attribute_list(self, k, i):
        r"""Ensure attribute *k* is a :class:`list` with *i* entries

        :Call:
            >>> testd._extend_attribute_list(k, i)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *k*: :class:`str`
                Name of attribute
            *i*: :class:`int`
                Command number
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Get the attribute
        V = getattr(self, k)
        # Check it
        if not isinstance(V, list):
            raise AttributeError("No list-type driver attribute '%s'" % k)
        # Number of entries in attribute
        n = len(V)
        # Append if needed
        for j in range(n, i+1):
            V.append(None)

    # Write title for command *i* with result
    def write_command_title(self, i):
        r"""Write the title for command *i*, with result

        :Call:
            >>> testd.write_command_title(i)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
        :Versions:
            * 2021-10-12 ``@ddalle``: Version 1.0
        """
        # Get subtitle
        subt = self.opts.getel("CommandTitles", i, vdef=None)
        # Create an indent
        tab = "    "
        # Status
        status = self.TestStatus_List[i]
        # Form the title for subsection
        if subt:
            # Include subtitle
            ttl = "Command %i: %s" % (i+1, subt)
        else:
            # No subtitle; just command number
            ttl = "Command %i" % (i+1)
        # Add result
        if self.TestStatus_List[i]:
            ttl += " (PASS)\n"
        else:
            ttl += " (**FAIL**)\n"
        # Stash results
        fp = self.get_results_summary(i)
        fp.prepend("\n\n")
        fp.prepend("-" * len(ttl))
        fp.prepend(ttl)

    # Start log output
    def write_command_summary(self, i, cmd):
        r"""Start the reST results summary for command *i*

        :Call:
            >>> testd.write_command_summary(i, cmd)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
            *cmd*: :class:`str`
                The command that was run in step *i*
        :Versions:
            * 2019-07-09 ``@ddalle``: Version 1.0
            * 2021-10-12 ``@ddalle``: Version 2.0; title elsewhere
        """
        # Create an indent
        tab = "    "
        # Stash results
        fp = self.get_results_summary(i)
        fp.write(":Command:\n")
        fp.write(tab)
        fp.write(".. code-block:: console\n\n")
        fp.write(tab + tab + "$ " + cmd)
        fp.write("\n\n")

    # Check return code status
    def process_results_returncode(self, i, ierr):
        r"""Check the return code against target for command *i*

        :Call:
            >>> q = testd.process_results_returncode(i, ierr)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
            *ierr*: :class:`int`
                Exit status from command *i*
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not *ierr* matches expected value
        :Attributes:
            *testd.TestReturnCode[i]*: *ierr*
                Return code save for future reference
            *testd.TestStatus_ReturnCode[i]*: *q*
                Whether or not *ierr* matches expected value
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Extend attributes as necessary
        self._extend_attribute_list("TestStatus_ReturnCode", i)
        self._extend_attribute_list("TestReturnCodes", i)
        # Target return code
        rc_target = self.opts.getel("ReturnCode", i, vdef=0)
        # Save the return code
        self.TestReturnCodes[i] = ierr
        # Check result
        q = (ierr == rc_target)
        # Check for nonzero exit status
        if q:
            # Update status lists
            self.TestStatus_ReturnCode[i] = True
        else:
            # Update status lists
            self.TestStatus_ReturnCode[i] = False
            # Fail the test and abort
            self.TestStatus = False
        # Stash results
        fp = self.get_results_summary(i)
        # Return code section
        fp.write(":Return Code:\n")
        # Write status of the test
        if q:
            fp.write("    * **PASS**\n")
        else:
            fp.write("    * **FAIL**\n")
        # Write targets
        fp.write("    * Output: ``%i``\n" % ierr)
        fp.write("    * Target: ``%i``\n" % rc_target) 
        # Output
        return q

    # Check timer status
    def process_results_maxtime(self, i, t):
        r"""Check the maximum time for command *i*

        :Call:
            >>> q = testd.process_results_maxtime(i, t)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
            *t*: :class:`float`
                Time used by command *i*
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not *t* exceeds proscribed *MaxTime*
        :Attributes:
            *testd.TestRunTimeList[i]*: *t*
                Execution time for command *i* saved
            *testd.TestRunTimeTotal*: :class:`float`
                Total execution time increased by *t*
            *testd.TestStatus_MaxTime[i]*: *q*
                Whether or not total time exceeds proscription
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Maximum time
        tmax = self.opts.getel("MaxTime", i, vdef=None)
        # Convert to seconds
        tsec = testshell._time2sec(tmax)
        # Number of entries in *TestStatus_MaxTime*
        ntest = len(self.TestStatus_MaxTime)
        # Check if already processed
        if i <= ntest - 1:
            return self.TestStatus_MaxTime[i]
        # Get preceding total time used
        ttot = self.TestRunTimeTotal
        # Update timers
        self.TestRunTimeList.append(t)
        self.TestRunTimeTotal += t
        # Process maximum time consideration
        if tsec:
            # Check for expiration
            q = (ttot + t < tsec)
        else:
            # No test to fail
            q = True
        # Save status
        self.TestStatus_MaxTime.append(q)
        # Update overall status
        self.TestStatus = self.TestStatus and q
        # Stash results
        fp = self.get_results_summary(i)
        # Return code section
        fp.write(":Time Taken:\n")
        # Write status of the test
        if q:
            fp.write("    * **PASS**\n")
        else:
            fp.write("    * **FAIL**\n")
        # Write time taken
        fp.write("    * Command took %.2f seconds\n" % t)
        if i > 0:
            fp.write("    * Cumulative time: %.2f seconds\n" % (ttot + t))
        # Write constraint
        if tsec:
            fp.write(
                "    * Max allowed: %.2f seconds (%s)\n" % (tsec, tmax))
        # Output
        return q

    # Check contents of STDOUT
    def process_results_stdout(self, i, fnout):
        r"""Compare STDOUT from command *i* to target

        :Call:
            >>> q = testd.process_results_stdout(i, fnout)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
            *fnout*: :class:`str`
                Name of file that captured STDOUT from command
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not STDOUT matched target (``True`` if no
                target specified)
        :Attributes:
            *testd.TestStatus_STDOUT[i]*: *q*
                Whether or not STDOUT matched target
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Get target STDOUT file
        fntout = self.opts.get_TargetSTDOUT(i)
        # Extend attributes as necessary
        self._extend_attribute_list("TestStatus_STDOUT", i)
        # Individual tests on whether STDOUT and TargetSTDOUT exist
        qtarget = fntout and isinstance(fntout, strlike)
        qactual = fnout  and isinstance(fnout,  strlike)
        # Absolutize the path to *fntout*; usually in parent folder
        if qtarget and not os.path.isabs(fntout):
            # If relative, compare to parent
            fntout = os.path.join(os.path.realpath(".."), fntout)
        # Check if files exist
        qtarget = qtarget and os.path.isfile(fntout)
        qactual = qactual and os.path.isfile(fnout)
        # Perform test on STDOUT
        if not fntout:
            # No target: PASS
            q = True
        elif not fnout:
            # No STDOUT file: unacceptable if target
            q = False
        elif not qactual:
            # STDOUT not mapped to file: unacceptable if target
            q = False
        else:
            # Get options for file comparisons
            kw_comp = self.opts.get_FileComparisonOpts(i)
            # Compare STDOUT files
            q, i2 = fileutils.compare_files(fnout, fntout, **kw_comp)
        # Save result
        self.TestStatus_STDOUT[i] = q
        # Update overall status
        self.TestStatus = self.TestStatus and q
        # Indentation
        tab = "    "
        # reST settings
        show_out = self.opts.getel("ShowSTDOUT", i, vdef=None)
        link_out = self.opts.getel("LinkSTDOUT", i, vdef=False)
        show_trg = self.opts.getel("ShowTargetSTDOUT", i, vdef=True)
        link_trg = self.opts.getel("LinkTargetSTDOUT", i, vdef=False)
        # Get language for Lexer
        lang = self.opts.getel("LexerSTDOUT", i, vdef="none")
        # Get output handle
        fp = self.get_results_summary(i)
        # Return code section
        fp.write(":STDOUT:\n")
        # Write status of the test
        if q:
            fp.write("    * **PASS**\n")
        else:
            fp.write("    * **FAIL**\n")
        # Show actual STDOUT
        if qactual and link_out:
            # Link file name
            flink = "STDOUT.%02i" % (i+1)
            # Copy the file
            shutil.copy(fnout, os.path.join(self.fdoc, flink))
            # Create the link
            fp.write(tab)
            fp.write("* Actual: :download:`%s`\n" % flink)
        elif qactual and (
                (show_out is None and not (q and show_trg)) or show_out):
            # Read it
            txt = open(fnout).read()
            # Check for content
            if len(txt) > 0:
                # Write header information
                fp.write(tab + "* Actual:\n\n")
                # Use language
                fp.write(tab + "  .. code-block:: %s\n\n" % lang)
                # Loop through lines
                for line in txt.split("\n"):
                    # Indent it 8 spaces
                    fp.write(tab + tab + line + "\n")
                # Blank line
                fp.write("\n")
            else:
                # Write empty actual
                fp.write(tab + "* Actual: (empty)\n")
        # Show target STDOUT
        if qtarget and link_trg:
            # Link file name
            flink = "STDOUT-target.%02i" % (i+1)
            # Copy the file
            shutil.copy(fnout, os.path.join(self.fdoc, flink))
            # Create the link
            fp.write(tab)
            fp.write("* Target: :download:`%s`\n" % flink)
        elif qtarget and show_trg:
            # Read it
            txt = open(fntout).read()
            # Check for content
            if len(txt) > 0:
                # Write header information
                fp.write(tab + "* Target:\n\n")
                # Use language
                fp.write(tab + "  .. code-block:: %s\n\n" % lang)
                # Loop through lines
                for line in txt.split("\n"):
                    # Indent it 8 spaces
                    fp.write(tab + tab + line + "\n")
                # Blank line
                fp.write("\n")
            else:
                # Write empty actual
                fp.write(tab + "* Target: (empty)\n")
        # Output
        return q

    # Check contents of STDERR
    def process_results_stderr(self, i, fnerr, fnout):
        r"""Compare STDERR from command *i* to target

        :Call:
            >>> q = testd.process_results_stderr(i, fnerr, fnout)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
            *fnerr*: :class:`str`
                Name of file that captured STDERR from command
            *fnout*: :class:`str`
                Name of file that captured STDOUT from command
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not STDERR matched target (``True`` if no
                target specified or if SDTERR mapped to STDOUT)
        :Attributes:
            *testd.TestStatus_STDERR[i]*: *q*
                Whether or not STDERR matched target
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2019-07-08 ``@ddalle``: Version 1.0
        """
        # Get target STDOUT file
        fnterr = self.opts.get_TargetSTDERR(i)
        # Extend attributes as necessary
        self._extend_attribute_list("TestStatus_STDERR", i)
        # Individual tests on whether STDERR and TargetSTDERR exist
        qtarget = fnterr and isinstance(fnterr, strlike)
        qactual = fnerr  and isinstance(fnerr,  strlike)
        # Absolutize the path to *fntout*; usually in parent folder
        if qtarget and not os.path.isabs(fnterr):
            # If relative, assume it's in parent folder
            fnterr = os.path.join(os.path.realpath(".."), fnterr)
        # Check if files exist
        qtarget = qtarget and os.path.isfile(fnterr)
        qactual = qactual and os.path.isfile(fnerr)
        # Perform test on STDERR
        if not fnterr:
            # No target: check for actual
            if not fnerr:
                # Neither
                q = True
            elif not isinstance(fnerr, strlike):
                # STDERR not mapped to file: unknowable
                q = True
            elif (fnerr == fnout):
                # STDERR mapped to STDOUT file; test elsewhere
                q = True
            elif os.path.isfile(fnerr):
                # Actual reported; check if it's empty
                q = os.path.getsize(fnerr) == 0
        elif not fnerr:
            # No STDERR file: unacceptable if target
            q = False
        elif not qactual:
            # STDERR not mapped to file: unacceptable if target
            q = False
        elif (fnerr == fnout):
            # STDERR mapped to STDOUT file; unacceptable if target
            q = False
        else:
            # Get options for file comparisons
            kw_comp = self.opts.get_FileComparisonOpts(i)
            # Target is in the parent folder
            if not os.path.isabs(fnterr):
                # If relative, compare to parent
                fnterr = os.path.join(os.path.realpath(".."), fnterr)
            # Compare STDOUT files
            q = fileutils.compare_files(fnerr, fnterr, **kw_comp)
        # Save result
        self.TestStatus_STDERR[i] = q
        # Update overall status
        self.TestStatus = self.TestStatus and q
        # Get output handle
        fp = self.get_results_summary(i)
        # Indentation
        tab = "    "
        # reST settings
        show_out = self.opts.getel("ShowSTDERR", i, vdef=None)
        link_out = self.opts.getel("LinkSTDERR", i, vdef=False)
        show_trg = self.opts.getel("ShowTargetSTDERR", i, vdef=True)
        link_trg = self.opts.getel("LinkTargetSTDERR", i, vdef=False)
        # Get language for Lexer
        lang = self.opts.getel("LexerSTDERR", i, vdef="none")
        # Return code section
        fp.write(":STDERR:\n")
        # Write status of the test
        if q:
            fp.write("    * **PASS**\n")
        else:
            fp.write("    * **FAIL**\n")
        # Show actual STDERR
        if qactual and link_out:
            # Link file name
            flink = "STDERR.%02i" % (i+1)
            # Copy the file
            shutil.copy(fnout, os.path.join(self.fdoc, flink))
            # Create the link
            fp.write(tab)
            fp.write("* Actual: :download:`%s`\n" % flink)
        elif qactual and (
                (show_out is None and not (q and show_trg)) or show_out):
            # Read it
            txt = open(fnerr).read()
            # Check for content
            if len(txt) > 0:
                # Write header information
                fp.write(tab + "* Actual:\n\n")
                # Use language
                fp.write(tab + "  .. code-block:: %s\n\n" % lang)
                # Loop through lines
                for line in txt.split("\n"):
                    # Indent it 8 spaces
                    fp.write(tab + tab + line + "\n")
                # Blank line
                fp.write("\n")
            else:
                # Write empty actual
                fp.write(tab + "* Actual: (empty)\n")
        # Show target STDERR
        if qtarget and link_trg:
            # Link file name
            flink = "STDERR-target.%02i" % (i+1)
            # Copy the file
            shutil.copy(fnout, os.path.join(self.fdoc, flink))
            # Create the link
            fp.write(tab)
            fp.write("* Target: :download:`%s`\n" % flink)
        elif qtarget and show_trg:
            # Read it
            txt = open(fnterr).read()
            # Check for content
            if len(txt) > 0:
                # Write header information
                fp.write(tab + "* Target:\n\n")
                # Use language
                fp.write(tab + "  .. code-block:: %s\n\n" % lang)
                # Loop through lines
                for line in txt.split("\n"):
                    # Indent it 8 spaces
                    fp.write(tab + tab + line + "\n")
                # Blank line
                fp.write("\n")
            else:
                # Write empty actual
                fp.write(tab + "* Actual: (empty)\n")
        # End section
        fp.write("\n")
        # Output
        return q

    # Test PNG
    def process_results_png(self, i):
        r"""Compare PNG results from command *i* to target

        :Call:
            >>> q = testd.process_results_png(i)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not PNG matched target (``True`` if no
                target specified)
        :Attributes:
            *testd.TestStatus_PNG[i]*: *q*
                Whether or not PNG matched target
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2020-03-16 ``@ddalle``: Version 1.0
        """
        # PNG file names
        fpngs_targ = self.opts.get_TargetPNG(i)
        fpngs_work = self.opts.get_PNG(i)
        # Check for something to check
        if fpngs_targ is None:
            return True
        # Extend attributes as necessary
        self._extend_attribute_list("TestStatus_PNG", i)
        # reST settings
        show_work = self.opts.getel("ShowPNG", i, vdef=True)
        link_work = self.opts.getel("LinkPNG", i, vdef=False)
        show_targ = self.opts.getel("ShowTargetPNG", i, vdef=True)
        link_targ = self.opts.getel("LinkTargetPNG", i, vdef=False)
        show_diff = self.opts.getel("ShowDiffPNG", i, vdef=False)
        link_diff = self.opts.getel("LinkDiffPNG", i, vdef=False)
        # Get tolerance
        tol = self.opts.get_PNGTol(i)
        # Initialize status as "success"
        status = 0
        # Check for matching-length lists
        if not isinstance(fpngs_targ, list):
            # Nonsense targets
            status = 101
        elif not isinstance(fpngs_work, list):
            # Nonsense outputs
            status = 102
        elif not all(
                [isinstance(fpng, strlike) for fpng in fpngs_targ]):
            # Nonsense target type
            status = 103
        elif not all(
                [isinstance(fpng, strlike) for fpng in fpngs_work]):
            # Nonsense working file name type
            status = 104
        elif len(fpngs_targ) != len(fpngs_work):
            # Mismatching lists
            status = 105
        else:
            # Absolutize the path to *fnpngs_targ*
            for (j, fpng) in enumerate(fpngs_targ):
                if not os.path.isabs(fpng):
                    fpngs_work[j] = os.path.join(os.path.realpath(".."), fpng)
            # Absolutize the path to *fnpngs_work*
            for (j, fpng) in enumerate(fpngs_work):
                if not os.path.isabs(fpng):
                    fpngs_work[j] = os.path.join(os.path.realpath("."), fpng)
            # Ensure pyplot is ready
            _import_pyplot()
            # Check for pyplot
            if plt is None:
                # Set status
                self.TestStatus_PNG[i] = False
                self.TestStatus = False
                return False
            # Loop through targets
            for (j, ftarg) in enumerate(fpngs_targ):
                # Get working file
                fwork = fpngs_work[j]
                # Check for both files
                if not os.path.isfile(ftarg):
                    # No target file
                    status = 200 + j
                    break
                elif not os.path.isfile(fwork):
                    # No working file
                    status = 300 + j
                    break
                # Read target image
                try:
                    # Attempt read
                    imtarg = plt.imread(ftarg)
                except Exception:
                    # Failed
                    status = 400 + j
                    break
                # Read working image
                try:
                    # Attempt read
                    imwork = plt.imread(fwork)
                except Exception:
                    # Failed
                    status = 500 + j
                    break
                # Check dimensionality
                if imtarg.ndim != imwork.ndim:
                    # Mismatching dimension
                    status = 600 + j
                    break
                elif imtarg.shape != imwork.shape:
                    # Mismatching size
                    status = 700 + j
                    break
                # Number of pixels
                npix = imwork.shape[0] * imwork.shape[1]
                # Difference
                imdiff = imwork - imtarg
                # Test matchy-matchiness
                if imwork.ndim == 3:
                    # root-sum-square in dimension 3
                    imsq = np.sqrt(np.sum(imdiff * imdiff, axis=2))
                else:
                    # Just use absolute value if no colors
                    imsq = np.abs(imdiff)
                # "Integrate" differences
                ndiff = np.sum(imsq)
                # Difference fraction
                frac_diff = ndiff / npix
                # Check tolerance
                if frac_diff > 1 - tol:
                    # Images too different
                    status = 800 + j
                    # Copy files if necessary
                    if (show_diff or link_diff):
                        # Name of output file
                        fndiff = "PNG-diff-%02i-%02i.png" % (i, j)
                        # Absolute
                        fdiff = os.path.join(self.fdoc, fndiff)
                        # Write it
                        plt.imsave(fdiff, imdiff)
                    # Exit
                    break
        # Overall status
        q = status == 0
        # Save result
        self.TestStatus_PNG[i] = q
        # Update overall status
        self.TestStatus = self.TestStatus and q
        # Get output handle
        fp = self.get_results_summary(i)
        # Indentation
        tab = "    "
        # Return code section
        fp.write(":PNG:\n")
        # Write status of the test
        if q:
            # Overall status
            fp.write("    * **PASS**\n")
            # Fraction
            fp.write("    * Difference fraction: %.4f\n" % frac_diff)
        else:
            # Overall status
            fp.write("    * **FAIL**\n")
            # Fraction if status sufficient
            if status >= 800:
                # Write fraction
                fp.write("    * Difference fraction: %.4f\n" % frac_diff)
        # Copy and include working images
        if (show_work and not (q and show_targ)) or link_work:
            # Subsection header
            fp.write(tab)
            fp.write("* Actual:\n")
            # Loop through files
            for k, fpng in enumerate(fpngs_work[:j+1]):
                # Skip cases if target shown
                if show_targ and show_work and (q or k < j):
                    continue
                # Name of copied image
                fname = "PNG-%02i-%02i.png" % (i, k)
                # Absolute paths
                fsrc = os.path.join(os.path.realpath("."), fpng)
                fout = os.path.join(self.fdoc, fname)
                # Check for source
                if not os.path.isfile(fsrc):
                    continue
                # Copy file
                shutil.copy(fsrc, fout)
                # Include instructions
                if show_work:
                    # Image directive
                    fp.write("\n")
                    fp.write(tab*2)
                    fp.write(".. image:: %s\n" % fname)
                    # Width instructions
                    fp.write(tab*3)
                    fp.write(":width: 4.5in\n")
                else:
                    # Include a link
                    fp.write(tab*2)
                    fp.write("- :download:`%s`\n" % fname)
            # Extra blank line
            fp.write("\n")
        # Copy and include target files
        if show_targ or link_targ:
            # Header
            fp.write(tab)
            fp.write("* Target:\n")
            # Loop through files
            for k, fpng in enumerate(fpngs_targ[:j+1]):
                # Name of copied image
                fname = "PNG-target-%02i-%02i.png" % (i, k)
                # Absolute paths
                fsrc = os.path.join(os.path.realpath(".."), fpng)
                fout = os.path.join(self.fdoc, fname)
                # Check for source
                if not os.path.isfile(fsrc):
                    continue
                # Copy file
                shutil.copy(fsrc, fout)
                # Include instructions
                if show_targ:
                    # Image directive
                    fp.write("\n")
                    fp.write(tab*2)
                    fp.write(".. image:: %s\n" % fname)
                    # Width instructions
                    fp.write(tab*3)
                    fp.write(":width: 4.5in\n")
                else:
                    # Include a link
                    fp.write(tab*2)
                    fp.write("- :download:`%s`\n" % fname)
            # Extra blank line
            fp.write("\n")
        # Copy and include diff
        if (status >= 800) and (show_diff or link_diff):
            # Header
            fp.write(tab)
            fp.write("* Diff:\n")
            # Include image
            if show_diff:
                # Image directive
                fp.write("\n")
                fp.write(tab*2)
                fp.write(".. image:: %s\n" % fdiff)
                # Width instructions
                fp.write(tab*3)
                fp.write(":width: 4.5in\n")
            else:
                # Include a link
                fp.write(tab*2)
                fp.write("- :download:`%s`\n" % fdiff)
            # Extra blank line
            fp.write("\n")
        # Output
        return q

    # Test file
    def process_results_file(self, i):
        r"""Compare files written from command *i* to target

        :Call:
            >>> q = testd.process_results_file(i)
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
            *i*: :class:`int`
                Command number
        :Outputs:
            *q*: ``True`` | ``False``
                Whether or not PNG matched target (``True`` if no
                target specified)
        :Attributes:
            *testd.TestStatus_File[i]*: *q*
                Whether or not file matched target
            *testd.TestStatus*: ``True`` | ``False``
                Set to ``False`` if above test fails
        :Versions:
            * 2020-04-01 ``@ddalle``: Version 1.0
        """
        # File names
        fnames_targ = self.opts.get_TargetFile(i)
        fnames_work = self.opts.get_CompareFile(i)
        # Check for something to check
        if fnames_targ is None:
            return True
        # Extend attributes as necessary
        self._extend_attribute_list("TestStatus_File", i)
        # reST settings
        show_work = self.opts.getel("ShowCompareFile", i, vdef=False)
        link_work = self.opts.getel("LinkCompareFile", i, vdef=True)
        show_targ = self.opts.getel("ShowTargetFile", i, vdef=False)
        link_targ = self.opts.getel("LinkTargetFile", i, vdef=True)
        #
        disp_work = show_work or link_work
        disp_targ = show_targ or link_targ
        # Get options for file comparisons
        kw_comp = self.opts.get_FileComparisonOpts(i)
        # Initialize status as "success"
        status = 0
        # Check for matching-length lists
        if not isinstance(fnames_targ, list):
            # Nonsense targets
            status = 101
        elif not isinstance(fnames_work, list):
            # Nonsense outputs
            status = 102
        elif not all(
                [isinstance(fname, strlike) for fname in fnames_targ]):
            # Nonsense target type
            status = 103
        elif not all(
                [isinstance(fname, strlike) for fname in fnames_work]):
            # Nonsense working file name type
            status = 104
        elif len(fnames_targ) != len(fnames_work):
            # Mismatching lists
            status = 105
        else:
            # Absolutize the path to *fnames_targ*
            for (j, fname) in enumerate(fnames_targ):
                if not os.path.isabs(fname):
                    fnames_work[j] = os.path.join(
                        os.path.realpath(".."), fname)
            # Absolutize the path to *fnpngs_work*
            for (j, fname) in enumerate(fnames_work):
                if not os.path.isabs(fname):
                    fnames_work[j] = os.path.join(
                        os.path.realpath("."), fname)
            # Loop through targets
            for (j, ftarg) in enumerate(fnames_targ):
                # Get working file
                fwork = fnames_work[j]
                # Check for both files
                if not os.path.isfile(ftarg):
                    # No target file
                    status = 200 + j
                    break
                elif not os.path.isfile(fwork):
                    # No working file
                    status = 300 + j
                    break
                # Compare STDOUT files
                qi = fileutils.compare_files(fwork, ftarg, **kw_comp)
                # Test
                if not qi:
                    # Files differ (according to *kw_comp* rules)
                    status = 500 + j
                    # Exit
                    break
        # Overall status
        q = status == 0
        # Save result
        self.TestStatus_File[i] = q
        # Update overall status
        self.TestStatus = self.TestStatus and q
        # Get output handle
        fp = self.frst
        # Indentation
        tab = "    "
        # Return code section
        fp.write(":Compare Files:\n")
        # Write status of the test
        if q:
            # Overall status
            fp.write("    * **PASS**\n")
        else:
            # Overall status
            fp.write("    * **FAIL**\n")
        # Copy and include working images
        if disp_work and not (q and disp_targ):
            # Header
            fp.write(tab)
            fp.write("* Actual:\n")
            # Loop through files
            for k, fname in enumerate(fnames_work[:j+1]):
                # Skip cases if target shown
                if disp_targ and disp_work and (q or k < j):
                    continue
                # Name of copied image
                flink = "FILE-%02i-%02i.txt" % (i, k)
                # Absolute paths
                fsrc = os.path.join(os.path.realpath("."), fname)
                fout = os.path.join(self.fdoc, flink)
                # Check for source
                if not os.path.isfile(fsrc):
                    continue
                # Include instructions
                if show_work:
                    # Read file
                    lines = open(fsrc).readlines()
                    # Check for content
                    if len(lines) > 0:
                        # Write directive to show file
                        fp.write("\n")
                        fp.write(tab*2)
                        fp.write("  .. code-block:: none\n\n")
                        # Loop through lines
                        for line in lines:
                            # Indent it 12 spaces
                            fp.write(tab*3)
                            fp.write(line)
                        # Blank line
                        fp.write("\n")
                else:
                    # Copy file
                    shutil.copy(fsrc, fout)
                    # Include a link
                    fp.write(tab*2)
                    fp.write("- :download:`%s`\n" % flink)
            # Extra blank line
            fp.write("\n")
        # Copy and include target files
        if disp_targ:
            # Header
            fp.write(tab)
            fp.write("* Target:\n")
            # Loop through files
            for k, fname in enumerate(fnames_targ[:j+1]):
                # Name of copied file
                flink = "FILE-target-%02i-%02i.txt" % (i, k)
                # Absolute paths
                fsrc = os.path.join(os.path.realpath(".."), fname)
                fout = os.path.join(self.fdoc, flink)
                # Check for source
                if not os.path.isfile(fsrc):
                    continue
                # Include instructions
                if show_targ:
                    # Image directive
                    fp.write("\n")
                    fp.write(tab*2)
                    fp.write(".. code-block:: none\n\n")
                    # Read file
                    lines = open(fsrc).readlines()
                    # Check for content
                    if len(lines) > 0:
                        # Write directive to show file
                        fp.write("\n")
                        fp.write(tab*2)
                        fp.write(tab + "  .. code-block:: none\n\n")
                        # Loop through lines
                        for line in lines:
                            # Indent it 12 spaces
                            fp.write(tab*3)
                            fp.write(line)
                        # Blank line
                        fp.write("\n")
                else:
                    # Copy file
                    shutil.copy(fsrc, fout)
                    # Include a link
                    fp.write(tab*2)
                    fp.write("- :download:`%s`\n" % flink)
            # Extra blank line
            fp.write("\n")
        # Output
        return q

    # Get results dictionary
    def get_results_dict(self):
        r"""Create a dictionary of results from the test

        :Call:
            >>> results = testd.get_results_dict()
        :Inputs:
            *testd*: :class:`cape.testutils.testd.TestDriver`
                Test driver controller
        :Outputs:
            *results*: :class:`dict`
                Dictionary of results with the following keys
            *TestStatus*: ``True`` | ``False``
                Overall result of the test
            *TestCommandsNum*: :class:`int` >= 0
                Number of commands proscribed
            *TestCommandsRun*: :class:`int` >= 0
                Number of commands actually run
            *TestStatus_ReturnCode*: :class:`list`\ [:class:`bool`]
                Return code test results for each command
            *TestStatus_MaxTime*: :class:`list`\ [:class:`bool`]
                Timeout test results for each command
            *TestStatus_STDOUT*: :class:`list`\ [:class:`bool`]
                STDOUT comparison test results for each command
            *TestStatus_STDERR*: :class:`list`\ [:class:`bool`]
                STDERR comparison test results for each command
            *TestStatus_PNG*: :class:`list`\ [:class:`bool`]
                PNG image comparison test results for each command
            *TestReturnCodes*: :class:`list`\ [:class:`int`]
                Return codes fro each command run
            *TestRunTimeTotal*: :class:`float`
                Total time taken by all commands run
            *TestRunTimeList*: :class:`list`\ [:class:`float`]
                Time taken by each command run
        :Versions:
            * 2019-07-09 ``@ddalle``: Version 1.0
        """
        # Create dictionary and return it
        return {
            "TestStatus":            self.TestStatus,
            "TestCommandsNum":       self.TestCommandsNum,
            "TestCommandsRun":       self.TestCommandsRun,
            "TestStatus_ReturnCode": self.TestStatus_ReturnCode,
            "TestStatus_MaxTime":    self.TestStatus_MaxTime,
            "TestStatus_STDOUT":     self.TestStatus_STDOUT,
            "TestStatus_STDERR":     self.TestStatus_STDERR,
            "TestStatus_PNG":        self.TestStatus_PNG,
            "TestStatus_File":       self.TestStatus_File,
            "TestReturnCodes":       self.TestReturnCodes,
            "TestRunTimeTotal":      self.TestRunTimeTotal,
            "TestRunTimeList":       self.TestRunTimeList,
        }


# Command-line interface
def cli(*a, **kw):
    r"""Test case command-line interface

    :Call:
        >>> results = cli(*a, **kw)
    :Inputs:
        *f*, *json*: {``"cape-test.json"``} | :class:`str`
            Name of JSON settings file for crawler
    :Outputs:
        *results*: :class:`dict`
            Dictionary of results with the following keys
        *TestStatus*: ``True`` | ``False``
            Overall result of the test
        *TestCommandsNum*: :class:`int` >= 0
            Number of commands proscribed
        *TestCommandsRun*: :class:`int` >= 0
            Number of commands actually run
        *TestStatus_ReturnCode*: :class:`list`\ [:class:`bool`]
            Return code test results for each command
        *TestStatus_MaxTime*: :class:`list`\ [:class:`bool`]
            Timeout test results for each command
        *TestStatus_STDOUT*: :class:`list`\ [:class:`bool`]
            STDOUT comparison test results for each command
        *TestStatus_STDERR*: :class:`list`\ [:class:`bool`]
            STDERR comparison test results for each command
        *TestReturnCodes*: :class:`list`\ [:class:`int`]
            Return codes fro each command run
        *TestRunTimeTotal*: :class:`float`
            Total time taken by all commands run
        *TestRunTimeList*: :class:`list`\ [:class:`float`]
            Time taken by each command run
    :Versions:
        * 2019-07-03 ``@ddalle``: Version 1.0
        * 2019-07-08 ``@ddalle``: Added output
    """
    # Get an instance of the crawler class
    testd = TestDriver(**kw)
    # Run the crawler
    return testd.run()


# Entry point
def main():
    r"""Run CAPE test crawler

    :Call:
        >>> main()
    :Versions:
        * 2021-10-15 ``@ddalle``: Version 1.0
    """
    # Parse command-line args
    a, kw = argread.readkeys(sys.argv)
    # Check for help flgas
    if kw.get("h") or kw.get("help"):
        print(HELP_TESTCASE)
        return
    # Call the function
    cli(*a, **kw)
