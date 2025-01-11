from typing import List, Dict
from decimal import Decimal
from django.db.models import Sum
from datetime import datetime, timedelta
from metatrade.services import MetaApiService
from ctrader.services import CTraderService
from trade_locker.services import TradeLockerService
from .models import ManualTrade, CustomUser, TradeAccount
from dateutil.parser import parse
from django.utils import timezone

class TradeService:

    @staticmethod
    def get_account_balance_chart(user, from_date: timezone.datetime = None, to_date: timezone.datetime = None) -> Dict:
        """
        Gets a balance chart for the given user
        """

        if from_date and to_date:
            from django.utils.timezone import make_aware

            from_date = make_aware(from_date)
            to_date = make_aware(to_date)

        trades = TradeService.get_all_trades(user, include_deposits=True)

        if not trades:
            return {}   

        # If from_date and to_date are not provided, use trade date range
        if not from_date:
            from_date = trades[-1]['close_date'] - timezone.timedelta(days=1)
        if not to_date:
            to_date = timezone.now()

        balance_chart = {}

        def add_for_date(date):
            trades_up_to_point = [
                trade for trade in trades 
                if trade['close_date'] <= date
            ]

            # Calculate cumulative profit/loss
            cumulative_profit = sum(
                Decimal(str(trade.get('profit', 0))) for trade in trades_up_to_point
            )

            balance_chart[date.strftime('%Y-%m-%d %H:%M:%S')] = cumulative_profit

        for trade in trades:
            add_for_date(trade['close_date'])

        add_for_date(from_date)
        add_for_date(to_date)
        inter_chart = balance_chart.copy()
        balance_chart = {}
        for(key, value) in inter_chart.items():
            if key >= from_date.strftime('%Y-%m-%d %H:%M:%S') and key <= to_date.strftime('%Y-%m-%d %H:%M:%S'):
                balance_chart[key] = value
                    
        return balance_chart

    
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
        # get CTrader accounts
        try:
            c_trader_accounts = CTraderService.fetch_accounts(user)
            accounts_summary['c_trader_accounts'] = c_trader_accounts
            c_trader_balance = sum(Decimal(str(account.get('balance', 0))) for account in c_trader_accounts)
            accounts_summary['total_balance'] += c_trader_balance

            # Add to combined accounts list
            for account in c_trader_accounts:
                accounts_summary['accounts'].append({
                    'id': account.get('id'),
                    'name': account.get('account', 'C-Trader Account'),
                    'balance': Decimal(str(account.get('balance', 0))),
                    'type': 'c_trader',
                    'last_updated': account.get('updated_at'),
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
    def get_all_trades(user, from_date: datetime = None, to_date: datetime = None, include_deposits=False) -> List[Dict]:
        """
        Fetches all trades from different sources and normalizes them
        """
        trades = []
        
        # Get manual trades
        if from_date and to_date:
            manual_trades = ManualTrade.objects.filter(account__user=user, close_date__range=(from_date, to_date))
        else:
            manual_trades = ManualTrade.objects.filter(account__user=user)  

        trades.extend([trade.to_dict() for trade in manual_trades])
        
        # Get MetaAPI trades
        try:
            meta_trades = [trade.to_dict() for trade in MetaApiService.fetch_trades(user=user, from_time=from_date, to_time=to_date, include_deposits=include_deposits)]
            trades.extend(meta_trades)
        except Exception as e:
            print(f"Error fetching meta trades: {str(e)}")
        # Get C Trader trades
        try:
            c_trades = [trade.to_dict() for trade in CTraderService.fetch_trades(user=user, from_time=from_date, to_time=to_date)]
            trades.extend(c_trades)
        except Exception as e:
            print(f"Error fetching meta trades: {str(e)}")
        
        trades.sort(key=lambda x: x['close_date'], reverse=True)

        return trades
    
    @staticmethod
    def calculate_session_distribution(trades: List[Dict]) -> Dict[str, float]:
        """
        Calculates the distribution of trades across sessions,
        normalized to a 0-1 scale where the most frequent session is 1.0
        """
        # Initialize counters for each session
        session_counts = {
            'london': 0,
            'new-york': 0,
            'asia': 0,
            'pacific': 0
        }

        london = 7, 13
        new_york = 13, 22
        pacific = 23, 0
        asia = 0, 6

        # Count trades for each session
        for trade in trades:
            trade_date = trade.get('trade_date')

            if trade_date:
                if isinstance(trade_date, str):
                    trade_date = parse(trade_date)

                if trade_date.hour >= london[0] and trade_date.hour <= london[1]:
                    session_counts['london'] += 1
                if trade_date.hour >= new_york[0] and trade_date.hour <= new_york[1]:
                    session_counts['new-york'] += 1
                if trade_date.hour >= pacific[0] and trade_date.hour <= pacific[1]:
                    session_counts['pacific'] += 1
                if trade_date.hour >= asia[0] and trade_date.hour <= asia[1]:
                    session_counts['asia'] += 1

        # Find the maximum count to normalize
        max_count = max(session_counts.values()) if session_counts.values() else 1

        # Normalize to 0-1 scale
        session_distribution = {
            session: count / max_count if max_count > 0 else 0
            for session, count in session_counts.items()
        }

        return {
            'distribution': session_distribution,
            'raw_counts': session_counts,
            'total_trades': sum(session_counts.values())
        }

    @staticmethod
    def calculate_day_of_week_distribution(trades: List[Dict]) -> Dict[str, float]:
        """
        Calculates the distribution of trades across days of the week,
        normalized to a 0-1 scale where the most frequent day is 1.0
        """
        # Initialize counters for each day
        day_counts = {
            'Monday': 0,
            'Tuesday': 0,
            'Wednesday': 0,
            'Thursday': 0,
            'Friday': 0,
            'Saturday': 0,
            'Sunday': 0
        }

        # Count trades for each day
        for trade in trades:
            trade_date = trade.get('trade_date') or trade.get('open_time')
            if trade_date:
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
                day_name = trade_date.strftime('%A')
                day_counts[day_name] += 1

        # Find the maximum count to normalize
        max_count = max(day_counts.values()) if day_counts.values() else 1

        # Normalize to 0-1 scale
        day_distribution = {
            day: count / max_count if max_count > 0 else 0
            for day, count in day_counts.items()
        }

        return {
            'distribution': day_distribution,
            'raw_counts': day_counts,
            'total_trades': sum(day_counts.values())
        }

    @staticmethod
    def calculate_statistics(trades: List[Dict], accounts: Dict) -> Dict:
        """
        Calculates comprehensive statistics for given trades
        """
        if not trades:
            return {
                'overall_statistics': {
                    'balance': Decimal('0'),
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_invested': Decimal('0'),
                    'win_rate': 0,
                    'long': 0,
                    'short': 0,
                    'best_win': 0,
                    'worst_loss': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'profit_factor': 0,
                    'total_won': 0,
                    'total_lost': 0,
                    'average_holding_time_minutes': 0,
                },
                'day_performances': {},
                'symbol_performances': [],
                'monthly_summary': []
            }

        # Overall statistics
        balance = accounts.get('total_balance', 0)
        total_trades = len(trades)
        total_profit = sum(Decimal(str(trade.get('profit', 0))) for trade in trades)
        total_invested = sum(Decimal(str(trade.get('total_amount', 0))) for trade in trades)
        winning_trades = len([t for t in trades if Decimal(str(t.get('profit', 0))) > 0])
        long = len([t for t in trades if t.get('trade_type') == 'BUY'])
        short = len([t for t in trades if t.get('trade_type') == 'SELL'])
        total_won = sum(Decimal(str(trade.get('profit', 0))) for trade in trades if trade.get('profit', 0) > 0)
        total_lost = abs(sum(Decimal(str(trade.get('profit', 0))) for trade in trades if trade.get('profit', 0) < 0))
       
        all_wins = [t.get('profit', 0) for t in trades if t.get('profit', 0) > 0]
        best_win = 0
        average_win = 0
        if all_wins:
            average_win = sum([t.get('profit', 0) for t in trades if t.get('profit', 0) > 0]) / len([t for t in trades if t.get('profit', 0) > 0])
            best_win = max(all_wins)
        

        all_losses = [t.get('profit', 0) for t in trades if t.get('profit', 0) < 0]
        worst_loss = 0
        average_loss = 0
        if all_losses:
            average_loss = sum([t.get('profit', 0) for t in trades if t.get('profit', 0) < 0]) / len([t for t in trades if t.get('profit', 0) < 0])
            worst_loss = min(all_losses)

        if total_lost == 0:
            profit_factor = 0
        else:
            profit_factor = Decimal(str(total_won / total_lost))
        timed_trades = [t.get('duration_in_minutes', 0) for t in trades if t.get('duration_in_minutes', 0) > 0]
        average_holding_time_minutes = 0

        if timed_trades != []:
            average_holding_time_minutes = sum(timed_trades) / len(timed_trades)

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

        # Day performance
        day_performances = {}
        for trade in trades:
            trade_date = trade.get('close_date') or trade.get('close_time')
            if not trade_date:
                continue
                
            if isinstance(trade_date, str):
                trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))

            day_key = trade_date.strftime('%Y-%m-%d')
            
            if day_key not in day_performances:
                day_performances[day_key] = {
                    'day': day_key,
                    'total_trades': 0,
                    'total_profit': Decimal('0'),
                    'total_won': Decimal('0'),
                    'total_loss': Decimal('0'),
                    'total_invested': Decimal('0')
                }
            
            day_performances[day_key]['total_trades'] += 1
            day_performances[day_key]['total_profit'] += Decimal(str(trade.get('profit', 0)))
            if trade.get('profit', 0) > 0:
                day_performances[day_key]['total_won'] += Decimal(str(trade.get('profit', 0)))
            else:    
                day_performances[day_key]['total_loss'] += Decimal(str(trade.get('profit', 0)))

            day_performances[day_key]['total_invested'] += Decimal(str(trade.get('total_amount', 0)))

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

        day_of_week_analysis = TradeService.calculate_day_of_week_distribution(trades)
        sessions_analysis = TradeService.calculate_session_distribution(trades)

        return {
            'overall_statistics': {
                'long': long,
                'short': short,
                'balance': balance,
                'total_trades': total_trades,
                'total_profit': total_profit,
                'total_invested': total_invested,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'best_win': best_win,
                'worst_loss': worst_loss,
                'average_win': average_win,
                'average_loss': average_loss,
                'profit_factor': profit_factor,                    
                'total_won': total_won,
                'total_lost': total_lost,
                'average_holding_time_minutes': average_holding_time_minutes,
            },
            'symbol_performances': list(symbol_stats.values()),
            'monthly_summary': list(monthly_stats.values()),
            'day_of_week_analysis': day_of_week_analysis,
            'day_performances': day_performances,
            'session_analysis': sessions_analysis,
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
