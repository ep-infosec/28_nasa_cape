r"""
:mod:`cape.pyfun.options.util`: Utilities for pyFun options module
===================================================================

This module provides tools to read, access, modify, and write settings
for :mod:`cape.pyfun`.  It is based off of the
:mod:`cape.cfdx.options.util` module and provides a special class
:class:`cape.cfdx.options.odict` that is subclassed from the Python
built-in :class:`dict`.  Behavior, such as ``opts['Namelist']`` or 
``opts.get('Namelist')`` are also present.  In addition, many
convenience methods such as ``opts.get_FUN3DNamelist()`` are provided.

In addition, this module controls default values of each pyFun
parameter in a three-step process.  The precedence used to determine
what the value of a given parameter should be is below.

    #. Values directly specified in the input file, :file:`pyFun.json`
    
    #. Values specified in the default control file,
       :file:`$PYKES/settings/pyFun.default.json`
    
    #. Hard-coded defaults from this module
    
:See Also:
    * :mod:`cape.cfdx.options.util`
    * :mod:`cape.pyfun.options`
"""

# Import CAPE options utilities
from ...cfdx.options.util import *


# Local folders
PYKES_OPTS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PYKES_FOLDER = os.path.dirname(PYKES_OPTS_FOLDER)


# Backup default settings
rc["ProjectName"] = "pykes"
    

# Function to ensure scalar from above
def rc0(p):
    r"""Get default from *cape.pykes.options.rc*; ensure a scalar
    
    :Call:
        >>> v = rc0(s)
    :Inputs:
        *s*: :class:`str`
            Name of parameter to extract
    :Outputs:
        *v*: any
            Either ``rc[s]`` or ``rc[s][0]``, whichever is appropriate
    :Versions:
        * 2014-08-01 ``@ddalle``: Version 1.0
    """
    # Use the `getel` function to do this.
    return getel(rc[p], 0)

    
# Function to get template
def get_template(fname):
    r"""Get the absolute path to a template file by name
    
    :Call:
        >>> fabs = get_template(fname)
    :Inputs:
        *fname*: :class:`str`
            Name of file, such as :file:`input.cntl`
    :Outputs:
        *fabs*: :class:`str`
            Full path to file
    :Versions:
        * 2021-10-18 ``@ddalle``: Version 1.0; from :mod:`cape.pyfun`
    """
    # Join with BaseFolder and 'templates'
    return os.path.join(PYKES_FOLDER, 'templates', fname)

    
# Function to get a template file name
def getKestrelTemplate(fname):
    r"""Get full path to template with file name *fname*
    
    :Call:
        >>> fabs = getKestrelTemplate(fname)
    :Inputs:
        *fname*: :class:`str`
            Name of file, such as :file:`input.cntl`
    :Outputs:
        *fabs*: :class:`str`
            Full path to the template file
    :Versions:
        * 2016-04-27 ``@ddalle``: Version 1.0
        * 2021-03-01 ``@ddalle``: Version 2.0; see :func:`get_template`    """
    # Get the full path
    return get_template(fname)


# Function to get the defautl settings.
def getPyKesDefaults():
    r"""Read ``pyKes.default.json`` default JSON file
    
    :Call:
        >>> defs = getPyKesDefaults()
    :Outputs:
        *defs*: :class:`dict`
            Dictionary of settings read from JSON file
    """
    # Fixed default file
    fname = os.path.join(PYKES_OPTS_FOLDER, "pyKes.default.json")
    # Process the default input file.
    return loadJSONFile(fname)

