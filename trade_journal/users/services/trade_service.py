from typing import List, Dict
from datetime import datetime

from ..models import AccountStatus, ManualTrade, CustomUser, TradeAccount, TradeType
from dateutil.parser import parse
from django.utils import timezone

class TradeService:

    @staticmethod
    def get_all_trades(user, from_date: datetime = None, to_date: datetime = None, include_deposits=False) -> List[ManualTrade]:
        """
        Fetches all trades from different sources and normalizes them
        """
        trades = ManualTrade.objects.filter(account__user=user)

        # Get manual trades
        if from_date and to_date:
            from django.utils.timezone import make_aware

            from_date = make_aware(from_date)
            to_date = make_aware(to_date)

            trades = trades.filter(close_time__range=(from_date, to_date))

        if not include_deposits:
            trades = trades.filter(is_top_up=False)

        return trades.order_by('-close_time').all()

    @staticmethod
    def get_account_balance_chart(user, from_date: timezone.datetime = None, to_date: timezone.datetime = None) -> Dict:
        """
        Gets a balance chart for the given user
        """

        trades = TradeService.get_all_trades(user, include_deposits=True)

        if from_date and to_date:
            from django.utils.timezone import make_aware

            from_date = make_aware(from_date)
            to_date = make_aware(to_date)
        else:
            last_trade = trades.last()
            if last_trade:
                from_date = trades.last().close_time - timezone.timedelta(days=1)
            else: 
                from_date = timezone.now() - timezone.timedelta(days=30)
            to_date = timezone.now()

        if not trades:
            return {}   

        balance_chart = {}

        def add_for_date(date, disallow_zero=False):
            trades_up_to_point = [
                trade for trade in trades 
                if trade.close_time <= date
            ]

            # Calculate cumulative profit/loss
            cumulative_profit = sum(
               trade.profit for trade in trades_up_to_point
            )

            if cumulative_profit == 0 and disallow_zero:
                return

            balance_chart[date.strftime('%Y-%m-%d %H:%M:%S')] = cumulative_profit

        add_for_date(from_date, disallow_zero=True)

        for trade in trades:
            add_for_date(trade.close_time)

        add_for_date(to_date)

        inter_chart = balance_chart.copy()

        balance_chart = {}
        
        for(key, value) in inter_chart.items():
            if key >= from_date.strftime('%Y-%m-%d %H:%M:%S') and key <= to_date.strftime('%Y-%m-%d %H:%M:%S'):
                balance_chart[key] = value
                    
        return balance_chart

    
    @staticmethod
    def get_all_accounts(user, status=None) -> List[TradeAccount]:

        accounts = TradeAccount.objects.filter(user=user)

        if status:
            accounts = accounts.filter(status=status)
        
        return accounts
    
    @staticmethod
    def get_account_performance(user) -> Dict:
        """
        Gets performance metrics for all accounts
        """
        performance = {
            'total_profit': 0,
            'total_trades': 0,
            'accounts_performance': [],
        }

        # Get all trades
        trades = TradeService.get_all_trades(user)
        
        # Calculate overall metrics
        for trade in trades:
            performance['total_profit'] += trade.profit
            performance['total_trades'] += 1

        # Get account-specific performance
        accounts = TradeService.get_all_accounts(user)

        for account in accounts:
            account_trades = [t for t in trades if t.account.id == account.id]

            account_performance = {
                'account_id': account.id,
                'account_name': account.account_name,
                'current_balance': account.balance,
                'total_trades': len(account_trades),
                'total_profit': sum(t.profit for t in account_trades),
                'last_updated': account.updated_at,
            }

            performance['accounts_performance'].append(account_performance)

        return performance
    
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
            trade_date = trade.open_time

            if trade_date:

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
    def calculate_day_of_week_distribution(trades: List[ManualTrade]) -> Dict[str, float]:
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
            trade_date = trade.open_time

            if trade_date:
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
    def calculate_statistics(trades: List[ManualTrade], accounts: List[TradeAccount]) -> Dict:
        """
        Calculates comprehensive statistics for given trades
        """
        if not trades:
            return {
                'overall_statistics': {
                    'balance': 0,
                    'total_trades': 0,
                    'total_profit': 0,
                    'total_invested': 0,
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

        # Balance
        balance = sum(account.balance for account in accounts)

        total_trades = len(trades)

        total_profit = sum(trade.profit for trade in trades)

        total_invested = sum(trade.quantity for trade in trades)

        winning_trades = len([t for t in trades if t.profit > 0])

        long = len([t for t in trades if t.trade_type == TradeType.buy])
        short = len([t for t in trades if t.trade_type == TradeType.sell])

        total_won = sum(trade.profit for trade in trades if trade.profit > 0)
        total_lost = abs(sum(trade.profit for trade in trades if trade.profit < 0))
       
        all_wins = [t.profit for t in trades if t.profit > 0]

        best_win = 0
        average_win = 0

        if all_wins:
            average_win = sum([t.profit for t in trades if t.profit > 0]) / len([t for t in trades if t.profit > 0])
            best_win = max(all_wins)
        

        all_losses = [t.profit for t in trades if t.profit < 0]
        worst_loss = 0
        average_loss = 0
        if all_losses:
            average_loss = sum([t.profit for t in trades if t.profit < 0]) / len([t for t in trades if t.profit < 0])
            worst_loss = min(all_losses)

        if total_lost == 0:
            profit_factor = 0
        else:
            profit_factor = total_won / total_lost
        timed_trades = [t.duration_in_minutes for t in trades if t.duration_in_minutes > 0]
        average_holding_time_minutes = 0

        if timed_trades != []:
            average_holding_time_minutes = sum(timed_trades) / len(timed_trades)

        # Symbol performances
        symbol_stats = {}
        for trade in trades:
            symbol = trade.symbol
            if not symbol:
                continue
                
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'symbol': symbol,
                    'total_trades': 0,
                    'total_profit': 0,
                    'total_invested': 0
                }
            
            symbol_stats[symbol]['total_trades'] += 1
            symbol_stats[symbol]['total_profit'] += trade.profit
            symbol_stats[symbol]['total_invested'] += trade.quantity

        # Day performance
        day_performances = {}
        for trade in trades:
            trade_date = trade.close_time
            if not trade_date:
                continue

            day_key = trade_date.strftime('%Y-%m-%d')
            
            if day_key not in day_performances:
                day_performances[day_key] = {
                    'day': day_key,
                    'total_trades': 0,
                    'total_profit': 0,
                    'total_won': 0,
                    'total_loss': 0,
                    'total_invested': 0,
                }
            
            day_performances[day_key]['total_trades'] += 1
            day_performances[day_key]['total_profit'] += trade.profit
            if trade.profit > 0:
                day_performances[day_key]['total_won'] += trade.profit
            else:    
                day_performances[day_key]['total_loss'] += trade.profit

            day_performances[day_key]['total_invested'] += trade.profit

        # Monthly summary
        monthly_stats = {}
        for trade in trades:
            trade_date = trade.open_time
            if not trade_date:
                continue
                
            month_key = trade_date.strftime('%Y-%m')
            
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month': month_key,
                    'total_trades': 0,
                    'total_profit': 0,
                    'total_invested': 0,
                }
            
            monthly_stats[month_key]['total_trades'] += 1
            monthly_stats[month_key]['total_profit'] += trade.profit
            monthly_stats[month_key]['total_invested'] += trade.profit

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
