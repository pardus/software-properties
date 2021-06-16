#!/usr/bin/python

import os
import unittest
import sys
sys.path.insert(0, "..")

import pycurl

from mock import patch

import softwareproperties.ppa
from  softwareproperties.ppa import (
    AddPPASigningKeyThread,
    mangle_ppa_shortcut,
    PPAException,
    verify_keyid_is_v4,
    )


MOCK_PPA_INFO={
    "displayname": "PPA for Michael Vogt",
    "web_link": "https://launchpad.net/~mvo/+archive/ppa", 
    "signing_key_fingerprint": "019A25FED88F961763935D7F129196470EB12F05",
    "name": "ppa",
    'distribution_link': 'https://launchpad.net/api/1.0/ubuntu',
    'owner_link': 'https://launchpad.net/api/1.0/~mvo',
    'reference': '~mvo/ubuntu/ppa',
    }


class LaunchpadPPATestCase(unittest.TestCase):

    @unittest.skipUnless(
        "TEST_ONLINE" in os.environ,
        "skipping online tests unless TEST_ONLINE environment variable is set")
    def test_ppa_info_from_lp(self):
        # use correct data
        info = softwareproperties.ppa.get_ppa_info_from_lp("mvo", "ppa")
        self.assertNotEqual(info, {})
        self.assertEqual(info["name"], "ppa")
        # use empty CERT file
        softwareproperties.ppa.LAUNCHPAD_PPA_CERT = "/dev/null"
        with self.assertRaises(PPAException) as cm:
            softwareproperties.ppa.get_ppa_info_from_lp("mvo", "ppa")
        self.assertEqual(
            cm.exception.original_error.args[0], pycurl.E_SSL_CACERT)

    def test_mangle_ppa_shortcut(self):
        self.assertEqual("~mvo/ubuntu/ppa", mangle_ppa_shortcut("ppa:mvo"))
        self.assertEqual(
            "~mvo/ubuntu/compiz", mangle_ppa_shortcut("ppa:mvo/compiz"))
        self.assertEqual(
            "~mvo/ubuntu-rtm/compiz",
            mangle_ppa_shortcut("ppa:mvo/ubuntu-rtm/compiz"))

    def test_mangle_ppa_shortcut_leading_slash(self):
        # Test for LP: #1426933
        self.assertEqual("~gottcode/ubuntu/gcppa",
                         mangle_ppa_shortcut("ppa:/gottcode/gcppa"))


class AddPPASigningKeyTestCase(unittest.TestCase):

    def setUp(self):
        self.t = AddPPASigningKeyThread("~mvo/ubuntu/ppa")

    @patch("softwareproperties.ppa.get_ppa_info_from_lp")
    @patch("softwareproperties.ppa.subprocess")
    def test_fingerprint_len_check(self, mock_subprocess, mock_get_ppa_info):
        """Test that short keyids (<160bit) are rejected""" 
        mock_ppa_info = MOCK_PPA_INFO.copy()
        mock_ppa_info["signing_key_fingerprint"] = "0EB12F05"
        mock_get_ppa_info.return_value = mock_ppa_info
        # do it
        res = self.t.add_ppa_signing_key("~mvo/ubuntu/ppa")
        self.assertFalse(res)
        self.assertFalse(mock_subprocess.Popen.called)
        self.assertFalse(mock_subprocess.call.called)

    @patch("softwareproperties.ppa.get_ppa_info_from_lp")
    @patch("softwareproperties.ppa.subprocess")
    def test_add_ppa_signing_key_wrong_fingerprint(self, mock_subprocess, mock_get_ppa_info):
        mock_get_ppa_info.return_value = MOCK_PPA_INFO
        mock_subprocess.call.return_value = 0
        with patch.object(self.t, "_get_fingerprints") as mock:
            # setup wrong fingerprint
            mock.return_value = ["48B913EC7093C0C675DADCC04BEF262422DF4087"]
            res = self.t.add_ppa_signing_key("~mvo/ubuntu/ppa")
            self.assertFalse(res)

    @patch("softwareproperties.ppa.get_ppa_info_from_lp")
    @patch("softwareproperties.ppa.subprocess")
    def test_add_ppa_signing_key_multiple_fingerprints(self, mock_subprocess, mock_get_ppa_info):
        mock_get_ppa_info.return_value = MOCK_PPA_INFO
        mock_subprocess.call.return_value = 0
        with patch.object(self.t, "_get_fingerprints") as mock:
            # setup multiple fingerprints
            mock.return_value = ["019A25FED88F961763935D7F129196470EB12F05",
                                 "48B913EC7093C0C675DADCC04BEF262422DF4087"]
            res = self.t.add_ppa_signing_key("~mvo/ubuntu/ppa")
            self.assertFalse(res)

    @patch("softwareproperties.ppa.get_ppa_info_from_lp")
    @patch("softwareproperties.ppa.subprocess")
    def test_add_ppa_signing_key_ok(self, mock_subprocess, mock_get_ppa_info):
        mock_get_ppa_info.return_value = MOCK_PPA_INFO
        mock_subprocess.call.return_value = 0
        # setup correct signing key
        with patch.object(self.t, "_get_fingerprints") as mock:
            mock.return_value = ["019A25FED88F961763935D7F129196470EB12F05"]
            res = self.t.add_ppa_signing_key("~mvo/ubuntu/ppa")
            self.assertTrue(res)
    
    def test_verify_keyid_is_v4(self):
        keyid = "0EB12F05"
        self.assertFalse(verify_keyid_is_v4(keyid))


if __name__ == "__main__":
    unittest.main()
