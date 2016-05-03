PyWinPath - a tool to manipulate the MS Windows PATH environment variable
=========================================================================

PyWinPath is an interactive command line tool to edit the %PATH% environment 
variable on Windows 7. 
The onboard tools for managing the content of %PATH% before Windows 10 
are barely existent and easily lead to a cluttered %PATH%. 
If the PATH is longer than a specific limit, Windows will silently omit 
the entries that exceed the maximum length and executables will not be found. 

PyWinPath tries to keep you sane when facing the %PATH%. There are many free tools 
to edit the %PATH%, however, I couldn't find a nice one in Python. 
Windows 10 has its own GUI to manipulate the %PATH%, I haven't seen it yet.

On Windows, the content of the %PATH% is generated 
from two registry values: the entries in the system-wide path followed by 
entries in the user-specific path. 

 * User path: ``HKEY_CURRENT_USER\Environment::PATH``
 * System path: ``HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment::Path``

PyWinPath lets you manipulate both of these registry values and does a 
couple of additional tricks, see the features listing below.

Developed and tested on Windows 7 (EN-US) with Python 3.5, so don't 
expect it to work in Python 2 or on other systems. Please let me know 
if it worked for you in other combinations, if not open an issue on 
Github, send me a patch or pull request.

Installation
------------

``pip install pywinpath``

Or if you want to see some colored output (this will install colorama):

``pip install pywinpath[color]``

Features
--------
    
 - Warns you of a too long %PATH% on Windows 7
 - Normalization of PATH entries followed by ...
 - Deduplication of system and user PATH variables
 - Purge non-existent directories from PATH variables
 - Shortening of PATH variables via junctions, e.g. 
   C:\Program Files\... gets C:\prg\...
 - Insert entries at the beginning of the PATH

ToDo
----

 - Add possibility to call with arguments instead of as interactive menu
 - Move entries up and down and between sys and user path (only after dedup?)
 - Handle variable expansions in PATH definitions such as %USERPROFILE%
 - Automatically identify efficient sub-paths for shortening via junctions
 - More tests
 - Test on other Windows-Python3 combinations than Windows 7 - Python 3.5
       
Notes
-----
    
 - With Git for Windows installed, the following command should display 
   a more readable PATH listing on the console: ``PATH | tr ; '\n'``
 - Junctions work for PATH shortening, also accross local drives:
     1) >mklink /J C:\prog(x86) "C:\Program Files (x86)"
     2) >set PATH=c:\prog(x86)\Notepad++;%PATH%
     3) Notepad++.exe is found.
     4) Junctions can be deleted by rmdir, the target dir is left untouched.

Motivated by Anaconda errors with too long paths::
    
    D:\proj>activate
    Deactivating environment "C:\Users\***\AppData\Local\Continuum\Anaconda3"...
    Activating environment "C:\Users\***\AppData\Local\Continuum\Anaconda3"...
    The input line is too long.
    "PATH_NO_SCRIPTS=C:\Users\***\AppData\Local\Continuum\Anaconda3;[...]"

Some links: 
    
  * Viewed about 40k times: http://superuser.com/questions/297947/is-there-a-convenient-way-to-edit-path-in-windows-7
  * Another PATH minipulation tool for the command line http://www.p-nand-q.com/download/gtools/pathed.html
  * http://stackoverflow.com/questions/34818282/anaconda-prompt-loading-error-the-input-line-is-too-long
  * http://stackoverflow.com/questions/19287379/how-do-i-add-to-the-windows-path-variable-using-setx-having-weird-problems
  * https://software.intel.com/en-us/articles/limitation-to-the-length-of-the-system-path-variable
  * http://betanews.com/2015/11/23/windows-10-finally-adds-a-new-path-editor/
    
