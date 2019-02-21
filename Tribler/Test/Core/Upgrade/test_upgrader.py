from __future__ import absolute_import

import os
import shutil

from pony.orm import db_session

from twisted.internet.defer import Deferred, inlineCallbacks

from Tribler.Core.Modules.MetadataStore.store import MetadataStore
from Tribler.Core.Upgrade.upgrade import TriblerUpgrader
from Tribler.Core.simpledefs import NTFY_STARTED, NTFY_UPGRADER_TICK
from Tribler.Test.Core.Upgrade.upgrade_base import AbstractUpgrader
from Tribler.Test.tools import trial_timeout


class TestUpgrader(AbstractUpgrader):

    @inlineCallbacks
    def setUp(self):
        yield super(TestUpgrader, self).setUp()
        self.upgrader = TriblerUpgrader(self.session)

    def test_run(self):
        """
        Test the run method of the upgrader
        """
        def check_should_upgrade():
            self.upgrader.failed = True
            return True, False
        self.upgrader.session.config.get_upgrader_enabled = lambda: True
        self.upgrader.check_should_upgrade_database = check_should_upgrade

        self.upgrader.run()
        self.assertTrue(self.upgrader.notified)

    @trial_timeout(10)
    def test_update_status_text(self):
        test_deferred = Deferred()

        def on_upgrade_tick(subject, changetype, objectID, status_text):
            self.assertEqual(status_text, "12345")
            test_deferred.callback(None)

        self.session.notifier.add_observer(on_upgrade_tick, NTFY_UPGRADER_TICK, [NTFY_STARTED])
        self.upgrader.update_status("12345")
        return test_deferred

    def test_upgrade_72_to_pony(self):
        OLD_DB_SAMPLE = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(os.path.realpath(__file__))), '..', 'data', 'upgrade_databases', 'tribler_v29.sdb'))
        old_database_path = os.path.join(self.session.config.get_state_dir(), 'sqlite', 'tribler.sdb')
        new_database_path = os.path.join(self.session.config.get_state_dir(), 'sqlite', 'metadata.db')
        channels_dir = os.path.join(self.session.config.get_chant_channels_dir())
        shutil.copyfile(OLD_DB_SAMPLE, old_database_path)
        self.upgrader.upgrade_72_to_pony()
        mds = MetadataStore(new_database_path, channels_dir, self.session.trustchain_keypair)
        with db_session:
            self.assertEqual(mds.TorrentMetadata.select().count(), 24)
        mds.shutdown()
