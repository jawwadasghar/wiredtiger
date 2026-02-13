#!/usr/bin/env python3
#
# Public Domain 2014-present MongoDB, Inc.
# Public Domain 2008-2014 WiredTiger, Inc.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import threading, time, wiredtiger, wttest
from helper_disagg import disagg_test_class, gen_disagg_storages
from wtscenario import make_scenarios

# test_layered72.py
#    Test reading the pinned history store on standby.
@disagg_test_class
class test_layered72(wttest.WiredTigerTestCase):
    conn_base_config = 'statistics=(all),disaggregated=(lose_all_my_data=true),'
    conn_config = conn_base_config + 'disaggregated=(role="leader")'

    create_session_config = 'key_format=S,value_format=S'

    uri = "layered:test_layered74"
    disagg_storages = gen_disagg_storages('test_layered74', disagg_only = True)
    scenarios = make_scenarios(disagg_storages)

    def test_layered74(self):
        print("--- start")
        # Create the follower
        conn_follow = self.wiredtiger_open('follower', self.extensionsConfig() + ',create,' +self.conn_base_config + 'disaggregated=(role="follower")')
        # session_follow = conn_follow.open_session('')

        # Create N tables
        for i in range(0, 100):
            self.assertEqual(self.session.create("layered:test_table" + str(i), "key_format=S,value_format=S"), 0)

        # Checkpoint
        self.session.checkpoint()

        print("--- disagg_advance_checkpoint 1")
        # Advance to the checkpoint
        self.disagg_advance_checkpoint(conn_follow)

        # # Create N tables
        # for i in range(101, 200):
        #     self.assertEqual(self.session.create("layered:test_table" + str(i), "key_format=S,value_format=S"), 0)

        # # Checkpoint
        # self.session.checkpoint()

        # print("--- disagg_advance_checkpoint 2")
        # # Advance to the checkpoint
        # self.disagg_advance_checkpoint(conn_follow)
