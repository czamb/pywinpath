# encoding: utf-8

__doc__ = """A command-line utility for Microsoft Windows that helps to
 keep the Windows PATH variable tidy and short."""
__version__ = '2016.05.03-beta3'
__author__ = 'github.com/czamb'

import os
import sys
import json
import glob
import msvcrt
import platform
import winreg
from collections import OrderedDict, namedtuple


try:
    import colorama
    colorama.init()
    from colorama import Fore, Back, Style
except:
    colorama = None


def time_str():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d_%Hh%Mm%Ss")


def uniquefy(lst, verbose=False):
    """Make entries of a list unique by keeping only the first
    occurrence of any item and preserve order"""
    seen = set()
    uniq = []
    for el in lst:
        if el not in seen:
            uniq.append(el)
            seen.add(el)
    if verbose:
        n_dupes = len(lst) - len(uniq)
        if n_dupes > 0:
            print('Removed %i duplicates' % n_dupes)
    return uniq


def stringify(path_list):
    return ';'.join(path_list)


def listify(path_str):
    """Convert path-string to list"""
    return [p.strip() for p in path_str.split(';')]


def print_header(header):
    print('==== %s ====' % header)


def stylify(style, text):
    """Use colorama if available"""
    if colorama and style in ('ok', 'warn'):
        styles = dict(ok=Fore.GREEN, warn=Fore.RED)
        text = styles[style] + Back.BLACK + text + Style.RESET_ALL
    return text


def normpath(path, verbose=True):
    """Normalize for better duplicate detection"""
    normalized = os.path.normcase(os.path.abspath(path))
    if verbose and path != normalized:
        print('Normalized %s' % path)
        print('        to %s' % normalized)
    return normalized


class WinPath():
    """A tool for manipulating Windows7 USER PATH and SYSTEM PATH
    variables which are concatenated to give the PATH variable on the
    command line.
    See also:
        >PATH
        >echo %PATH%
        >setx
    """

    def __init__(self):
        if platform.system() != 'Windows':
            msg = stylify('warn', 'This tool is only useful on Windows systems, aborting...')
            sys.exit(msg)
        self.limit = 2047  # Windows 7 character limit
        self.selected = None
        self.read_from_registry()
        self.check_registry_writeable()
        # https://software.intel.com/en-us/articles/limitation-to-the-length-of-the-system-path-variable
        sys_root = os.getenv('SystemRoot')
        self.vital_paths = self.normalize(
            [p for p in [os.path.join(sys_root, 'system32'), sys_root]],
            verbose=False)

    def read_from_registry(self):
        self.reg_user = get_path('user', verbose=False)
        self.reg_sys = get_path('system', verbose=False)
        self.store_initial()
        self.reg_user = self.normalize(get_path('user'), verbose=True)
        self.reg_sys = self.normalize(get_path('system'), verbose=True)

    def normalize(self, path_list, verbose=True):
        return uniquefy([normpath(p, verbose=verbose) for p in path_list],
                        verbose=verbose)

    def store_initial(self):
        """Save initial change to check for unsaved changes"""
        self.orig_user = self.reg_user[:]
        self.orig_sys = self.reg_sys[:]

    @property
    def unsaved_changes(self):
        return any([self.reg_user != self.orig_user,
                    self.reg_sys != self.orig_sys])

    def check_registry_writeable(self):
        """Check if the calling user has privilege to write to the registry"""
        self.writeable_user = True
        self.writeable_sys = True
        try:
            user_env = registry_open(user_key, writeable=True)
            winreg.CloseKey(user_env)
        except WindowsError:
            self.writeable_user = False
        try:
            sys_env = registry_open(sys_key, writeable=True)
            winreg.CloseKey(sys_env)
        except WindowsError:
            self.writeable_sys = False

    @property
    def plist(self):
        """Get the list of path values as it would be found in a cmd"""
        return self.reg_sys + self.reg_user

    def show_env_path(self):
        print_header('PATH Variable in current environment')
        path = os.getenv('PATH')
        path_lst = path.split(';')
        for p in path_lst:
            print(p)
        print('PATH has %i entries and a total length of %i chars.' %
              (len(path_lst), len(path)))

    def show(self):
        total_len = -1  # start at -1 bcs first entry has no leading ';'
        warned = False
        for idx, p in enumerate(self.plist):
            total_len += 1 + len(p)  # +1 bcs of the ';'
            if total_len > self.limit and not warned:
                print(stylify('warn', '/!\ Following entries will '
                              'not be in the %%PATH%%'))
                warned = True
            print(self.format_entry(idx, p))
        self.print_legend()

    def print_legend(self):
        print('Legend:')
        print('S: path found in system env (HKEY_LOCAL_MACHINE\%s::Path)' % sys_key.subkey)
        print('U: path found in user env (HKEY_CURRENT_USER\%s::PATH)' % user_key.subkey)
        print('*: directory does not exist')

    def format_entry(self, idx, entry):
        """Format a single entry in PATH for display"""
        nonex = entry in self.non_existent
        info_str = '%4i.' % idx
        info_str += [' ', '*'][nonex]
        info_str += ['---', 'S'][entry in self.reg_sys]
        if entry in self.reg_sys:
            info_str += '%2i' % self.reg_sys.index(entry)
        info_str += [' ---', ' U'][entry in self.reg_user]
        if entry in self.reg_user:
            info_str += '%2i' % self.reg_user.index(entry)
        if nonex:
            entry += ' [ N O T  F O U N D ]'
            entry = stylify('warn', entry)
        return "%s %s" % (info_str, entry)

    def select(self, substr):
        print('Showing only entries containing "%s"' % substr)
        self.selected = OrderedDict()
        self.rest = OrderedDict()
        for idx, p in enumerate(self.plist):
            if substr.lower() in p.lower():
                self.selected[idx] = p
                print('%s' % self.format_entry(idx, p))
            else:
                self.rest[idx] = p
        self.print_legend()
        any_key()

    def replace_prog_files_with_junctions(self):
        created_junctions = create_junctions()
        len_user0 = len(stringify(self.reg_user))
        len_sys0 = len(stringify(self.reg_sys))
        for orig, short in created_junctions.items():
            print('Replacing "%s" with "%s"' % (orig, short))
            self.reg_user = [p.replace(orig, short) for p in self.reg_user]
            self.reg_user = [p.replace(orig.lower(), short) for p in self.reg_user]
            self.reg_sys = [p.replace(orig, short) for p in self.reg_sys]
            self.reg_sys = [p.replace(orig.lower(), short) for p in self.reg_sys]
        self.reg_user = uniquefy(self.reg_user)
        self.reg_sys = uniquefy(self.reg_sys)
        len_user = len(stringify(self.reg_user))
        len_sys = len(stringify(self.reg_sys))
        print('Shortened USER PATH by %i chars' % (len_user0 - len_user))
        print('Shortened SYSTEM PATH by %i chars\n' % (len_sys0 - len_sys))

    def front(self, substr):
        self.select(substr)
        self.plist = self.selected.values() + self.rest.values()
        self.write()

    def show_registry(self):
        def print_path(label, plist):
            print('== ' + label + ' ==')
            for p in plist:
                print(p)
        print_path('USER PATH', get_path('user'))
        print_path('SYSTEM PATH', get_path('system'))

    def delete(self, to_delete=None):
        self.reg_user = [p for p in self.reg_user if p not in to_delete]
        # Do not delete important entries from system path
        to_delete = [td for td in to_delete if td.lower() not in self.vital_paths]
        self.reg_sys = [p for p in self.reg_sys if p not in to_delete]

    def delete_ui(self, to_delete=None):
        if to_delete is None:
            print(stylify('warn', 'Call delete with an index, such as \'d 23\''))
            return
        for del_entry in to_delete:
            print()
            if del_entry.lower() in self.vital_paths:
                print('%s will not be removed from system path' % del_entry)
                if del_entry.lower() in [p.lower() for p in self.reg_user]:
                    print('But it is also contained in USER PATH')
                else:
                    continue
            else:
                print(del_entry)
            print('  Delete this entry? [y]/n): ')
            resp = input()
            if resp.lower() in ['', 'y', 'yes']:
                self.delete([del_entry])
                print('Removed %s' % del_entry)

    def insert(self):
        print('Insert value into [u]ser or [s]ystem path: ', end='')
        resp = input().strip().lower()
        if resp in ['u', 's']:
            print('Value to insert: ', end='')
            path_lst = listify(input().strip())
            for path in self.normalize(path_lst[::-1]):
                if resp == 'u':
                    self.reg_user.insert(0, path)
                elif resp == 's':
                    self.reg_sys.insert(0, path)
                print('Value inserted.')
        else:
            print('Canceled.')

    @property
    def non_existent(self):
        nonex = []
        for p in self.plist:
            if not os.path.exists(p):
                nonex.append(p)
        return nonex

    def purge(self):
        """Delete non-existent dirs"""
        self.delete_ui(self.non_existent)
        print(stylify('ok', 'Deleted all non-existent directories.'))

    def dedup(self):
        self.dedup_answer = ''
        for p in self.plist:
            if (p in self.reg_user) and (p in self.reg_sys):
                print()
                print(p)
                print('  Remove from [u]ser path / [s]ystem path / [b]oth / [n]one (skip) / [c]ancel?')
                if self.dedup_answer:
                    answer = input(
                        '  (enter applies previous choice: %s)' %
                        self.dedup_answer)
                    if answer.strip():
                        # answer non-empty, use it
                        self.dedup_answer = answer
                else:
                    self.dedup_answer = input()
                if self.dedup_answer.lower() in ['q', 'c']:
                    print('  Canceled')
                    break
                if self.dedup_answer.lower() in ['b', 'both']:
                    self.delete([p])
                    print('  Removed %s from user and system path.' % p)
                if self.dedup_answer.lower() in ['u', 'user']:
                    self.reg_user = [rup for rup in self.reg_user if rup != p]
                    print('  Removed %s from user path.' % p)
                if self.dedup_answer.lower() in ['s', 'sys']:
                    self.reg_sys = [rsp for rsp in self.reg_sys if rsp != p]
                    print('  Removed %s from system path.' % p)

    def backup_to_file(self, comment=''):
        path_dict = dict(USER_PATH=stringify(self.reg_user),
                         SYSTEM_PATH=stringify(self.reg_sys))
        fname = 'path_vars_backup' + time_str()
        if comment:
            fname += '_%s' % comment
        # Write path data to json file
        with open(fname + '.json', 'w') as f_out:
            json.dump(path_dict, f_out)
        print('PATH vars written to %s' % fname + '.json')
        # old text output
        fname += '.txt'
        with open(fname, 'w+') as f:
            f.write('USER PATH:\n')
            f.write(stringify(self.reg_user))
            f.write('\nSYSTEM PATH:\n')
            f.write(stringify(self.reg_sys))
        print('PATH vars written to %s' % fname)

    @property
    def duplicates(self):
        return set(self.reg_user).intersection(set(self.reg_sys))

    def save_to_registry(self):
        os.system('cls')
        set_path('user', stringify(self.reg_user))
        set_path('system', stringify(self.reg_sys))
        self.store_initial()
        print('To see the effect open a new cmd.exe')

    def load_from_file(self, fname=None):
        os.system('cls')
        files = glob.glob('*.json')
        if fname is None:
            if files:
                for idx, f in enumerate(files):
                    print('%i - %s' % (idx, f))
            else:
                print('No JSON backup files found.')
            print('r - read from registry')
            print('c - cancel')
        print('Either enter the file number or one of the options: ', end='')
        resp = input()
        try:
            f_in = files[int(resp)]
        except:
            if resp.lower() in ['', 'c', 'q']:
                print('Canceled.')
                return
            if resp.lower() in ['r']:
                self.read_from_registry()
                return
            print('/!\ Couldn\'t load this file')
            return
        with open(f_in, 'r') as in_file:
            path_vars = json.load(in_file)
        self.reg_user = self.normalize(listify(path_vars['USER_PATH']))
        self.reg_sys = self.normalize(listify(path_vars['SYSTEM_PATH']))
        self.store_initial()
        print('Variables loaded.')

    def check_lengths(self, verbose=True):
        user_str = stringify(self.reg_user)
        sys_str = stringify(self.reg_sys)
        lu = len(user_str)
        ls = len(sys_str)
        len_total = lu + 1 + ls
        if verbose:
            print('  USER PATH has %4i chars' % lu)
            print('SYSTEM PATH has %4i chars' % ls)
            print(' --> %%PATH%% has %i chars' % len_total)
        pct = 100. * len_total / self.limit
        if len_total > self.limit:
            if verbose:
                print_header(stylify('warn', 'WARNING'))
                print(stylify('warn', '/!\ %%PATH%% exceeds the limit of %i characters.' % self.limit))
                print(stylify('warn', '/!\ Windows will silently omit entries in your PATH.'))
            else:
                print(stylify('warn', 'Your PATH is too long :(\n %i%% of %i available chars.' %
                      (pct, self.limit)))
        else:
            print(stylify('ok', 'Everything OK :)\n%%PATH%% has %i of %i available chars: %i%% full.' %
                  (len_total, self.limit, pct)))
        if verbose:
            any_key()
        return pct / 100.


__registry_values__ = """
https://msdn.microsoft.com/en-us/library/windows/desktop/ms724884(v=vs.85).aspx
REG_EXPAND_SZ:
A null-terminated string that contains unexpanded references to environment variables (for example, "%PATH%").
It will be a Unicode or ANSI string depending on whether you use the Unicode or ANSI functions.
To expand the environment variable references, use the ExpandEnvironmentStrings function.

REG_SZ:
A null-terminated string. This will be either a Unicode or an ANSI string,
depending on whether you use the Unicode or ANSI functions.
"""

RegKey = namedtuple('RegKey', ['key', 'subkey', 'name', 'type_'])
# type is either winreg.REG_EXPAND_SZ or winreg.REG_SZ

# Registry data for USER PATH variable
user_key = RegKey(winreg.HKEY_CURRENT_USER,
                  r'Environment', 'PATH', winreg.REG_SZ)

# Registry data for SYSTEM PATH variable
sys_key = RegKey(winreg.HKEY_LOCAL_MACHINE,
                 r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
                 'Path', winreg.REG_SZ)

reg_keys = {'user': user_key,
            'system': sys_key}


def registry_open(full_key, writeable=False):
    if writeable:
        access = winreg.KEY_ALL_ACCESS
    else:
        access = winreg.KEY_READ
    return winreg.OpenKey(full_key.key, full_key.subkey, 0, access)


def get_path(user_or_system, verbose=True):
    """Get user or stystem path from registry"""
    # http://stackoverflow.com/questions/21138014/how-to-add-to-and-remove-from-systems-environment-variable-path
    if verbose:
        print('Reading %s PATH from registry...' % user_or_system.upper(), end='')
    full_key = reg_keys[user_or_system]
    open_key = registry_open(full_key)
    try:
        path, _ = winreg.QueryValueEx(open_key, full_key.name)
        winreg.CloseKey(open_key)
        if verbose:
            print('OK.')
    except WindowsError as e:
        print('Error reading value from: %s' %
              (full_key.subkey + ' - ' + full_key.name))
        print('%s' % e)
        path = ''
    return listify(path)


def set_path(user_or_system, value):
    """Write user or stystem path to registry"""
    print('Saving %s PATH to registry ... ' % user_or_system.upper(), end='')
    full_key = reg_keys[user_or_system]
    try:
        open_key = registry_open(full_key, writeable=True)
    except WindowsError as e:
        print('Couldn\'t set %s path. Try running as administrator: '
              % user_or_system)
        print(e)
    else:
        winreg.SetValueEx(open_key, full_key.name, 0, full_key.type_, value)
        winreg.CloseKey(open_key)
        _broadcast_changes()
        print('OK.')


def _broadcast_changes():
    """Notify the system about the changes"""
    import win32gui
    import win32con
    win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')


def windows_path_gui():
    """Brings up the GUI to edit the PATH variables manually"""
    os.system('control system')
    # os.system("C:\\Windows\\system32\\\\rundll32.exe sysdm.cpl,EditEnvironmentVariables")


def windows_apps_gui():
    os.system('control appwiz.cpl')


def print_title():
    title = 'PyWinPath system path manipulation'
    print('\n' + '=' * (len(title) + 10))
    print_header(title)
    print('\n version %s' % __version__)
    print('')


def any_key():
    print('Press any key to continue.', end='\r')
    msvcrt.getch()
    print('  '*20)


# Common paths that can be replaced by shorter junctions
junctions = {'C:\\Program Files (x86)\\': 'C:\\prgx86\\',
             'C:\\Program Files\\': 'C:\\prg\\'}
# Order by length from long to short, so that partial paths cannot be replaced before a full match is found
junctions = OrderedDict(sorted(junctions.items(), key=lambda tup: len(tup[0]), reverse=True))


def create_junctions():
    """Junctions can be removed with rmdir"""
    print('Creating junctions for common directories...')
    valid_junctions = {}
    for orig, short in junctions.items():
        create = True
        if os.path.isdir(orig):
            print('%s' % orig)
            if os.path.isdir(short):
                if not os.path.samefile(orig, short):
                    print('%s and %s are not the same.' % (short, orig))
                    continue
                else:
                    print(' ... %s already exists.' % short)
                create = False
            valid_junctions[orig] = short
            if create:
                cmd = r'mklink /J %s "%s"' % (short, orig)
                print(cmd)
                os.system(cmd)
    return valid_junctions


class InteractiveMenu():
    """interactive menu"""

    def __init__(self):
        self.menu = OrderedDict()

    def cls(self):
        os.system('cls')

    def display_menu(self):
        for k, desc in self.menu.items():
            print('  %s - %s' % (k, desc[0]))

    def clean_input(self):
        return input().strip().lower()

    def ask_input(self, msg, default_resp=''):
        print(msg + ' [%s]' % default_resp + ': ', end='')
        resp = self.clean_input()
        if resp == '':
            resp = default_resp
        return resp


def main():
    import re

    def print_help():
        print_header('HELP')
        print("It is save to try out any operations.\n",
              "Only copies of the USER PATH and SYSTEM PATH values are changed.\n"
              "Nothing is written to the system until you save the PATH values\n"
              "to the registry or insert them manually into the graphical user\n"
              "interface provided by Windows.\n")
        any_key()

    def really_quit():
        if wp.unsaved_changes:
            print('Discard unsaved changes?  yes / [cancel]: ')
            yn = msvcrt.getch().lower()
            if yn != b'y':
                print('Canceled.')
                return False
        return True

    d_and_index = re.compile('^d\s([\d\s]*)')
    flt_substr = re.compile('^f\s(.*)')

    os.system('cls')
    m = InteractiveMenu()
    resp = ''
    while resp.lower() != 'q':
        print_title()
        try:
            wp
        except:
            wp = WinPath()
        wp.check_lengths(verbose=False)
        print('\nOptions:')
        m.menu.clear()
        m.menu['b'] = ('Backup to file', 'wp.backup_to_file()')
        m.menu['l'] = ('Load path variables from file or registry', 'wp.load_from_file()')
        m.menu['v'] = ('View %i entries: %i in SYSTEM PATH, %i in USER PATH' %
                       (len(wp.plist), len(wp.reg_sys), len(wp.reg_user)), 'wp.show()')
        m.menu['f'] = ('Filter entries, e.g. "f python"', 'wp.select(sub_str)')
        if wp.non_existent:
            m.menu['p'] = ('Purge %i non-existent entries' % len(wp.non_existent), 'wp.purge()')
        if wp.duplicates:
            m.menu['dedup'] = (stylify(
                'warn', '%i entries are in user AND system path' %
                len(wp.duplicates)), 'wp.dedup()')
        m.menu['shorten'] = ('Replace common long paths by shorter ones',
                             'wp.replace_prog_files_with_junctions()')
        m.menu['d'] = ('Delete an entry, e.g. "d 22 23" deletes 22nd and 23rd entry of [v]iew listing', 'wp.delete_ui()')
        m.menu['a'] = ('Add an entry', 'wp.insert()')
        # m.menu['m'] = ('Move an entry', 'print("not implemented yet")')
        m.menu['r'] = ('Display path info currently in registry', 'wp.show_registry()')
        m.menu['env'] = ('Display %PATH% of current environment', 'wp.show_env_path()')
        # m.menu['w'] = ('Write path strings to file', 'wp.write()')
        m.menu['ui'] = ('Open windows dialog to edit environment variables', 'windows_path_gui()')
        # menu['apps'] = ('Open windows dialog to add/remove sofware', 'windows_apps_gui()')
        # menu['t'] = ('Run tests', 'run_tests()')
        m.menu['c'] = ('Check lengths', 'wp.check_lengths()')
        msg = ''
        if wp.unsaved_changes:
            msg += stylify('warn', ' unsaved changes ')
        if not wp.writeable_sys:
            msg += ('\n      [' + stylify('warn', ' Warning:') + ' no permission for SYSTEM PATH,'
                    '\n      try \'Run as administrator\']')
        m.menu['s'] = ('Save values to registry' + msg, 'wp.save_to_registry()')
        m.menu['h'] = ('Print help', 'print_help()')
        m.menu['q'] = ('Quit', None)
        m.display_menu()
        resp = m.ask_input('What do you want to do?', 'v')
        del_match = d_and_index.match(resp)
        flt_match = flt_substr.match(resp)
        if resp in m.menu or del_match or flt_match:
            if del_match:
                idx_to_delete = del_match.group(1).split(' ')
                to_delete = [wp.plist[int(idx)] for idx in idx_to_delete]
                wp.delete_ui(to_delete)
            elif flt_match:
                sub_str = flt_match.group(1)
                exec(m.menu['f'][1])
            elif resp == 'q':
                if not really_quit():
                    resp = ''
            else:
                exec(m.menu[resp][1])
        else:
            m.cls()
            print("Unknown command '%s', please select one of the options." % resp)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
