from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from .services import MetaApiService
from .models import MetaTraderAccount, Trade
from datetime import datetime
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class MetaApiServiceProductionTest(TestCase):
    """
    To run these tests specifically:
    python manage.py test trade_journal.metatrade.tests.MetaApiServiceProductionTest
    """

    user: User
    account: MetaTraderAccount

    def setUp(self):
        self.account = MetaTraderAccount.objects.first()

        if(self.account is None):
            raise ValueError("No test account found. Please set up a test account first.")
        
        self.user = User.objects.first()
        logger.info(f"Testing account: {self.account.account_name} (ID: {self.account.account_id})")

    def test_live_account_connection(self):
        """Test connecting to a live MetaTrader account"""
        try:
            # Fetch accounts (this triggers refresh)
            accounts = MetaApiService.fetch_accounts(self.user)
            self.assertTrue(len(accounts) > 0, "No accounts returned")
            
            # Refresh account from database
            self.account.refresh_from_db()
            logger.info(f"Balance updated from {self.initial_balance} to {self.account.balance}")
            
            # Verify cache timestamps
            self.assertIsNotNone(self.account.cached_at, "Cache timestamp not set")
            self.assertGreater(self.account.cached_until, datetime.now(), "Cache expiration incorrect")
            
            # Test trade fetching
            trades = MetaApiService.fetch_trades(self.user)
            logger.info(f"Found {len(trades)} trades")
            
            # Validate trades
            for trade in trades:
                self.assertEqual(trade['account_id'], self.account.id)
                self.assertIsInstance(trade['profit'], (int, float))
                self.assertIsInstance(trade['volume'], (int, float))
                self.assertTrue(trade['symbol'], "Trade symbol missing")

        except Exception as e:
            logger.error(f"Production test failed: {str(e)}")
            raise

    def test_trade_history_consistency(self):
        """Test trade history data consistency"""
        try:
            # Fetch trades twice
            trades1 = MetaApiService.fetch_trades(self.user)
            trades2 = MetaApiService.fetch_trades(self.user)
            
            # Compare results
            self.assertEqual(len(trades1), len(trades2), 
                           "Inconsistent trade counts between fetches")
            
            # Check trade details consistency
            trades_dict1 = {t['trade_id']: t for t in trades1}
            trades_dict2 = {t['trade_id']: t for t in trades2}
            
            self.assertEqual(trades_dict1.keys(), trades_dict2.keys(), 
                           "Trade IDs don't match between fetches")

        except Exception as e:
            logger.error(f"Trade history consistency test failed: {str(e)}")
            raise

    def test_cache_mechanism(self):
        """Test the caching mechanism"""
        try:
            # First fetch to set cache
            MetaApiService.fetch_accounts(self.user)
            self.account.refresh_from_db()
            first_cache_time = self.account.cached_at
            
            # Immediate second fetch shouldn't update cache
            MetaApiService.fetch_accounts(self.user)
            self.account.refresh_from_db()
            
            self.assertEqual(self.account.cached_at, first_cache_time, 
                           "Cache updated too soon")

        except Exception as e:
            logger.error(f"Cache mechanism test failed: {str(e)}")
            raise

    def tearDown(self):
        # This runs after each test method
        logger.info(f"Test completed for account: {self.account.account_id}")

