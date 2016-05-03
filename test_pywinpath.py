# run with    py.test -sv
import unittest
from unittest.mock import patch  # mock is new in python 3.3

from pywinpath import *


class TestPyWinPath(unittest.TestCase):

    @patch('builtins.input', lambda: 'q')
    # @patch('msvcrt.getch', lambda: '_')
    def test_basic(self):
        main()

    @patch('builtins.input', lambda: 'q')
    @patch('builtins.input', lambda: 'notacommand')
    def test_unknown_command(self):
        main()

    def test_view(self):
        wp = WinPath()
        wp.reg_user = listify(stringify(['user56789'] * 105))
        wp.reg_sys = listify(stringify(['sys456789'] * 100))
        wp.show()

    @patch('builtins.input', lambda: 'u')
    def test_deduplication(self):
        wp = WinPath()
        wp.reg_user = listify('p1;p2')
        wp.reg_sys = listify('p2;p3')
        self.assertEqual(len(wp.duplicates), 1)
        wp.dedup()
        self.assertEqual(len(wp.duplicates), 0)
        self.assertEqual(len(wp.reg_user), 1)
        self.assertEqual(len(wp.reg_sys), 2)

    @patch('builtins.input', lambda: 'y')
    def test_purge(self):
        wp = WinPath()
        wp.reg_user = listify('p1')
        wp.reg_sys = listify('p2')
        self.assertEqual(len(wp.plist), 2)
        wp.purge()
        self.assertEqual(len(wp.plist), 0)

    def test_delete_and_unsaved_changes(self):
        wp = WinPath()
        wp.reg_user = listify('p1')
        wp.reg_sys = listify('p2')
        wp.store_initial()
        self.assertEqual(wp.unsaved_changes, False)
        self.assertEqual(len(wp.plist), 2)
        wp.delete(['p1'])
        self.assertEqual(len(wp.plist), 1)
        self.assertEqual(wp.unsaved_changes, True)
        wp.delete(['p2'])
        self.assertEqual(len(wp.plist), 0)
        self.assertEqual(wp.unsaved_changes, True)

    def test_vital_path_protection(self):
        wp = WinPath()
        wp.reg_user = listify('C:\\WinDOWS\\')
        wp.reg_sys = listify('C:\\WinDOWS;C:\\Windows\\system32')
        self.assertEqual(len(wp.plist), 3)
        wp.delete(wp.plist)
        # vital paths can only be deleted from user path
        self.assertEqual(len(wp.plist), 2)


class TestRegistryWrites(unittest.TestCase):
    @unittest.skip("skipping because it would change local registry temporarily")
    def test_set_user_path_in_registry(self):
        """This one is dangerous because it modifies the registry"""
        orig = stringify(get_path('user'))
        suffix = ';test'
        changed_path = orig + suffix
        set_path('user', changed_path)
        retrieved_path = stringify(get_path('user'))
        set_path('user', orig)
        self.assertEqual(changed_path, retrieved_path)
