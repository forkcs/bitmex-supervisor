import unittest

from supervisor import Supervisor
from supervisor.core import settings
from supervisor.core.interface import Exchange


class SupervisorCycleTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange = Exchange(symbol=settings.TEST_SYMBOL, api_key=settings.TEST_API_KEY,
                                 api_secret=settings.TEST_API_SECRET, test=True, connect_ws=False)
        self.supervisor = Supervisor(interface=self.exchange)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()
        self.exchange.exit()

    def test_run_cycle(self):
        self.supervisor.run_cycle()
        self.assertTrue(self.supervisor._run_thread.is_set())
        self.assertFalse(self.supervisor._exit_sync_thread.is_set())
        self.assertFalse(self.supervisor._stopped.is_set())
        self.assertTrue(self.supervisor.sync_thread.is_alive())

    def test_exit_cycle(self):
        self.supervisor.run_cycle()
        self.assertTrue(self.supervisor.sync_thread.is_alive())

        self.supervisor.exit_cycle()
        self.assertFalse(self.supervisor.sync_thread.is_alive())

    def test_stop_cycle(self):
        self.supervisor.run_cycle()
        self.supervisor.stop_cycle()

        self.assertTrue(self.supervisor._stopped.is_set())
        self.assertFalse(self.supervisor._run_thread.is_set())

    def test_continue_cycle(self):
        self.supervisor.run_cycle()
        self.supervisor.stop_cycle()
        self.supervisor.run_cycle()

        self.assertTrue(self.supervisor._run_thread.is_set())
        self.assertFalse(self.supervisor._exit_sync_thread.is_set())
        self.assertFalse(self.supervisor._stopped.is_set())
        self.assertTrue(self.supervisor.sync_thread.is_alive())
