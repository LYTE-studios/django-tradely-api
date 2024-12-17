from typing import List, Dict
from decimal import Decimal
from django.db.models import Sum
from datetime import datetime
from metatrade.services import MetaApiService
from trade_locker.services import TradeLockerService
from .models import ManualTrade, CustomUser, TradeAccount

class TradeService:
    
    @staticmethod
    def get_all_accounts(user) -> Dict:
        """
        Gets all accounts with their balances from all sources
        Returns a comprehensive summary of accounts and total balance
        """
        accounts_summary = {
            'total_balance': Decimal('0'),
            'accounts': [],
            'meta_accounts': [],
            'trade_locker_accounts': [],
        }

        # Get MetaAPI accounts
        try:
            meta_accounts = MetaApiService.fetch_accounts(user)
            accounts_summary['meta_accounts'] = meta_accounts
            meta_balance = sum(Decimal(str(account.get('balance', 0))) for account in meta_accounts)
            accounts_summary['total_balance'] += meta_balance

            # Add to combined accounts list
            for account in meta_accounts:
                accounts_summary['accounts'].append({
                    'id': account.get('id'),
                    'name': account.get('name', 'Meta Account'),
                    'balance': Decimal(str(account.get('balance', 0))),
                    'type': 'meta_api',
                    'last_updated': account.get('cached_at'),
                    'details': account
                })
        except Exception as e:
            print(f"Error fetching meta accounts: {str(e)}")

        # Get TradeLocker accounts
        try:
            trade_locker_accounts = TradeLockerService.fetch_accounts(user)
            accounts_summary['trade_locker_accounts'] = trade_locker_accounts
            trade_locker_balance = sum(Decimal(str(account.get('balance', 0))) for account in trade_locker_accounts)
            accounts_summary['total_balance'] += trade_locker_balance

            # Add to combined accounts list
            for account in trade_locker_accounts:
                accounts_summary['accounts'].append({
                    'id': account.get('id'),
                    'name': account.get('account_name', 'Trade Locker Account'),
                    'balance': Decimal(str(account.get('balance', 0))),
                    'type': 'trade_locker',
                    'last_updated': account.get('last_updated'),
                    'details': account
                })
        except Exception as e:
            print(f"Error fetching trade locker accounts: {str(e)}")

        # Get Manual Trade accounts
        try:
            manual_accounts = TradeAccount.objects.filter(user=user)
            manual_accounts_data = []
            
            for account in manual_accounts:
                account_data = {
                    'id': account.id,
                    'name': account.name,
                    'balance': account.balance,
                    'created_at': account.created_at,
                    'trades_count': account.trades.count()
                }
                manual_accounts_data.append(account_data)
                accounts_summary['total_balance'] += account.balance

                # Add to combined accounts list
                accounts_summary['accounts'].append({
                    'id': account.id,
                    'name': account.name,
                    'balance': account.balance,
                    'type': 'manual',
                    'last_updated': account.updated_at,
                    'details': account_data
                })

            accounts_summary['manual_accounts'] = manual_accounts_data
        except Exception as e:
            print(f"Error fetching manual trade accounts: {str(e)}")

        return accounts_summary

    @staticmethod
    def get_account_performance(user) -> Dict:
        """
        Gets performance metrics for all accounts
        """
        performance = {
            'total_profit': Decimal('0'),
            'total_trades': 0,
            'accounts_performance': [],
            'by_account_type': {
                'meta_api': {'profit': Decimal('0'), 'trades': 0},
                'trade_locker': {'profit': Decimal('0'), 'trades': 0},
                'manual': {'profit': Decimal('0'), 'trades': 0}
            }
        }

        # Get all trades
        trades = TradeService.get_all_trades(user)
        
        # Calculate overall metrics
        for trade in trades:
            trade_profit = Decimal(str(trade.get('profit', 0)))
            performance['total_profit'] += trade_profit
            performance['total_trades'] += 1

            # Track by account type
            account_type = trade.get('account_type', 'manual')
            performance['by_account_type'][account_type]['profit'] += trade_profit
            performance['by_account_type'][account_type]['trades'] += 1

        # Get account-specific performance
        accounts = TradeService.get_all_accounts(user)
        for account in accounts['accounts']:
            account_trades = [t for t in trades if t.get('account_id') == account['id']]
            account_performance = {
                'account_id': account['id'],
                'account_name': account['name'],
                'account_type': account['type'],
                'current_balance': account['balance'],
                'total_trades': len(account_trades),
                'total_profit': sum(Decimal(str(t.get('profit', 0))) for t in account_trades),
                'last_updated': account['last_updated']
            }
            performance['accounts_performance'].append(account_performance)

        return performance
    
    @staticmethod
    def refresh_all_accounts(user, force_refresh: bool = True) -> Dict[str, List[str]]:
        """
        Refreshes all accounts (MetaAPI and TradeLocker) for a user
        Returns a summary of the refresh operations
        """
        refresh_summary = {
            'success': [],
            'failed': []
        }

        # Refresh MetaAPI accounts
        try:
            MetaApiService.refresh_caches_sync(user, force_refresh=force_refresh)
            refresh_summary['success'].append('MetaAPI accounts')
        except Exception as e:
            print(f"Error refreshing MetaAPI accounts: {str(e)}")
            refresh_summary['failed'].append(f'MetaAPI accounts: {str(e)}')

        # Refresh TradeLocker accounts
        try:
            TradeLockerService.refresh_all_accounts(user)
            refresh_summary['success'].append('TradeLocker accounts')
        except Exception as e:
            print(f"Error refreshing TradeLocker accounts: {str(e)}")
            refresh_summary['failed'].append(f'TradeLocker accounts: {str(e)}')

        return refresh_summary
    
    @staticmethod
    def get_all_trades(user) -> List[Dict]:
        """
        Fetches all trades from different sources and normalizes them
        """
        trades = []
        
        # Get manual trades
        manual_trades = ManualTrade.objects.filter(account__user=user)
        trades.extend([trade.to_dict() for trade in manual_trades])
        
        # Get MetaAPI trades
        try:
            meta_trades = [trade.to_dict() for trade in MetaApiService.fetch_trades(user=user)]
            trades.extend(meta_trades)
        except Exception as e:
            print(f"Error fetching meta trades: {str(e)}")
        
        return trades

    @staticmethod
    def calculate_statistics(trades: List[Dict]) -> Dict:
        """
        Calculates comprehensive statistics for given trades
        """
        if not trades:
            return {
                'overall_statistics': {
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_invested': Decimal('0'),
                    'win_rate': 0,
                },
                'symbol_performances': [],
                'monthly_summary': []
            }

        # Overall statistics
        total_trades = len(trades)
        total_profit = sum(Decimal(str(trade.get('profit', 0))) for trade in trades)
        total_invested = sum(Decimal(str(trade.get('total_amount', 0))) for trade in trades)
        winning_trades = len([t for t in trades if Decimal(str(t.get('profit', 0))) > 0])
        
        # Symbol performances
        symbol_stats = {}
        for trade in trades:
            symbol = trade.get('symbol')
            if not symbol:
                continue
                
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'symbol': symbol,
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_invested': Decimal('0')
                }
            
            symbol_stats[symbol]['total_trades'] += 1
            symbol_stats[symbol]['total_profit'] += Decimal(str(trade.get('profit', 0)))
            symbol_stats[symbol]['total_invested'] += Decimal(str(trade.get('total_amount', 0)))

        # Monthly summary
        monthly_stats = {}
        for trade in trades:
            trade_date = trade.get('trade_date') or trade.get('open_time')
            if not trade_date:
                continue
                
            if isinstance(trade_date, str):
                trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                
            month_key = trade_date.strftime('%Y-%m')
            
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month': month_key,
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_invested': Decimal('0')
                }
            
            monthly_stats[month_key]['total_trades'] += 1
            monthly_stats[month_key]['total_profit'] += Decimal(str(trade.get('profit', 0)))
            monthly_stats[month_key]['total_invested'] += Decimal(str(trade.get('total_amount', 0)))

        return {
            'overall_statistics': {
                'total_trades': total_trades,
                'total_profit': total_profit,
                'total_invested': total_invested,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0
            },
            'symbol_performances': list(symbol_stats.values()),
            'monthly_summary': list(monthly_stats.values())
        }

    @staticmethod
    def get_leaderboard():
        """
        Calculates leaderboard across all trade sources
        """
        leaderboard = []
        
        for user in CustomUser.objects.all():
            trades = TradeService.get_all_trades(user)
            stats = TradeService.calculate_statistics(trades)
            
            leaderboard.append({
                'username': user.username,
                'total_profit': stats['overall_statistics']['total_profit'],
                'total_trades': stats['overall_statistics']['total_trades'],
                'win_rate': stats['overall_statistics']['win_rate']
            })
        
        return sorted(leaderboard, key=lambda x: x['total_profit'], reverse=True)
