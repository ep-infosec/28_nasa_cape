r"""
:mod:`cape.pyfun.manage`: Manage pyFun case folders
=====================================================

This module is a derivative of the main solution folder management 
module :mod:`cmanage`.  It provides FUN3D-specific versions of the 
three top-level functions, which each correspond to a primary 
command-line option.

    =======================   ==================
    Function                  Command-line
    =======================   ==================
    :func:`CleanFolder`       ``--clean``
    :func:`ArchiveFolder`     ``--archive``
    :func:`SkeletonFolder`    ``--skeleton``
    =======================   ==================
    
The FUN3D-specific versions of these commands use the function
:func:`pyFun.options.Archive.auto_Archive`, which apply the default 
settings appropriate to pyFun, and then call the generic version of the function with the same name from :mod:`cmanage`.  In addition, this 
module sets

    .. code-block:: python
        
        # Subdirectories
        fsub = ["Flow"]
        
which instructs the archiving functions to also look inside the folder
``Flow/`` if it exists.

The ``--unarchive`` command does not require any specific 
customizations for FUN3D, and the generic version of :func:`cmanage.UnarchiveFolder` is just called directly.

:See also:
    * :mod:`cmanage`
    * :mod:`cape.pyfun.options.Archive`
    * :mod:`cape.options.Archive`
"""

# Local imports
from .options import Archive
from .. import manage as cmanage


# Subdirectories
fsub = ["Flow"]


# Clear folder
def CleanFolder(opts, phantom=False):
    r"""Delete files before archiving and regardless of status
    
    :Call:
        >>> pyFun.manage.CleanFolder(opts, phantom=False)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface including management/archive interface
        *phantom*: ``True`` | {``False``}
            Write actions to ``archive.log``; only delete if ``False``
    :Versions:
        * 2017-03-10 ``@ddalle``: First version
        * 2017-12-15 ``@ddalle``: Added *phantom* option
    """
    # Restrict options to correct class
    opts = Archive.auto_Archive(opts)
    # Call the :mod:`cape` version
    cmanage.CleanFolder(opts, fsub=fsub, phantom=phantom)


# Archive folder
def ArchiveFolder(opts, phantom=False):
    r"""Archive a folder to a backup location and clean up nonessential 
    files
    
    :Call:
        >>> pyFun.manage.ArchiveFolder(opts, phantom=False)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface including management/archive interface
        *phantom*: ``True`` | {``False``}
            Write actions to ``archive.log``; only delete if ``False``
    :Versions:
        * 2016-12-09 ``@ddalle``: First version
        * 2017-12-15 ``@ddalle``: Added *phantom* option
    """
    # Restrict options to correct class
    opts = Archive.auto_Archive(opts)
    # Call the :mod:`cape` version
    cmanage.ArchiveFolder(opts, fsub=fsub, phantom=phantom)


# Replace folder contents with skeleton
def SkeletonFolder(opts, phantom=False):
    r"""Archive a folder to a backup location and clean up nonessential 
    files
    
    :Call:
        >>> pyFun.manage.SkeletonFolder(opts, phantom=False)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface including management/archive interface
        *phantom*: ``True`` | {``False``}
            Write actions to ``archive.log``; only delete if ``False``
    :Versions:
        * 2017-12-14 ``@ddalle``: First version
    """
    # Restrict options to correct class
    opts = Archive.auto_Archive(opts)
    # Call the :mod:`cape` version
    cmanage.SkeletonFolder(opts, fsub=fsub, phantom=phantom)
# def SkeletonFolder

