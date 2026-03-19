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

# test_layered79.py
#   Test that cursor.reserve() succeeds on a follower for a key that exists
#   only in the stable table (i.e. written by the leader and checkpointed).

import wiredtiger, wttest
from helper_disagg import disagg_test_class, gen_disagg_storages
from wtscenario import make_scenarios

# TODO: MAKE CODE LESS DUPLICATED !!!
# TODO: ADD TEST VARIANTS FOR INSERT/UPDATE/MODIFY/SEARCH/SEARCH_NEAR/REMOVE/ETC...

@disagg_test_class
class test_layered79(wttest.WiredTigerTestCase):
    conn_config = 'statistics=(all),precise_checkpoint=true,' \
                  'disaggregated=(role="leader")'

    uri = 'layered:test_layered79'

    disagg_storages = gen_disagg_storages('test_layered79', disagg_only=True)
    scenarios = make_scenarios(disagg_storages)

    conn_follow = None
    session_follow = None

    def create_follower(self):
        self.conn_follow = self.wiredtiger_open(
            'follower',
            self.extensionsConfig() + ',create,statistics=(all),' +
            'disaggregated=(role="follower")')
        self.session_follow = self.conn_follow.open_session('')

    def test_reserve_key_in_stable_table(self):
        """
        Create a table on the leader, insert entries, checkpoint, let the
        follower pick up the checkpoint, then call reserve() on the follower
        for a key that exists only in the stable table.
        """
        # Create table on the leader and insert a few keys under a transaction.
        self.session.create(self.uri, 'key_format=i,value_format=S')

        nkeys = 10
        cursor = self.session.open_cursor(self.uri)
        for i in range(1, nkeys + 1):
            self.session.begin_transaction()
            cursor[i] = 'value' + str(i)
            self.session.commit_transaction('commit_timestamp=' + self.timestamp_str(i))
        cursor.close()

        # Advance the stable timestamp to make all inserts stable, then checkpoint.
        self.conn.set_timestamp('stable_timestamp=' + self.timestamp_str(nkeys))
        self.session.checkpoint()

        # Open a follower and advance it to the latest checkpoint.
        self.create_follower()
        self.disagg_advance_checkpoint(self.conn_follow)

        # On the follower, call reserve() for a key that exists only in the
        # stable table (it was never written to the follower's ingest table).
        reserve_key = 5
        cursor_follow = self.session_follow.open_cursor(self.uri)
        self.session_follow.begin_transaction()
        cursor_follow.set_key(reserve_key)
        # reserve() should succeed (return 0) because the key exists in the stable table.
        self.assertEqual(cursor_follow.reserve(), 0)
        # After a successful reserve(), the cursor should be positioned on the key
        # and get_value() should return the previously written value.
        self.assertEqual(cursor_follow.get_value(), 'value' + str(reserve_key))
        self.session_follow.rollback_transaction()
        cursor_follow.close()

    def test_reserve_non_existent_key_on_follower(self):
        """
        Verify that reserve() returns WT_NOTFOUND for a key that does not
        exist in either the stable or ingest table on the follower.
        """
        self.session.create(self.uri, 'key_format=i,value_format=S')

        nkeys = 5
        cursor = self.session.open_cursor(self.uri)
        for i in range(1, nkeys + 1):
            self.session.begin_transaction()
            cursor[i] = 'value' + str(i)
            self.session.commit_transaction('commit_timestamp=' + self.timestamp_str(i))
        cursor.close()

        self.conn.set_timestamp('stable_timestamp=' + self.timestamp_str(nkeys))
        self.session.checkpoint()

        self.create_follower()
        self.disagg_advance_checkpoint(self.conn_follow)

        # Key 99 was never inserted, so reserve() should fail with WT_NOTFOUND.
        cursor_follow = self.session_follow.open_cursor(self.uri)
        self.session_follow.begin_transaction()
        cursor_follow.set_key(99)
        self.assertRaises(wiredtiger.WiredTigerError, lambda: cursor_follow.reserve())
        self.session_follow.rollback_transaction()
        cursor_follow.close()
