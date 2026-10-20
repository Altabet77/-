"""
business_metrics_tool.py — سمير: تكامل الأعمال الكامل
Stripe + Google Analytics + Instagram Graph API
تقرير صباحي ذكي + تنبيهات anomaly
"""

import os
import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.business_metrics')


# ──────────────────────────────────────────────────────────────────────────────
# STRIPE — تتبع الدخل والمبيعات
# ──────────────────────────────────────────────────────────────────────────────

async def tool_get_stripe_metrics(days: int = 1) -> Dict[str, Any]:
    """
    اجلب احصائيات Stripe: الدخل، العملاء الجدد، والمدفوعات.
    days: عدد الايام الماضية للمقارنة (افتراضي: يوم واحد)
    """
    stripe_key = os.getenv('STRIPE_SECRET_KEY', '')
    if not stripe_key:
        return {
            'status': 'not_configured',
            'message': 'Stripe غير مفعل. اضف STRIPE_SECRET_KEY في ملف .env',
            'revenue': 0, 'new_customers': 0, 'transactions': 0
        }

    loop = asyncio.get_event_loop()

    def _fetch():
        try:
            import stripe
            stripe.api_key = stripe_key

            since = int((datetime.now() - timedelta(days=days)).timestamp())

            charges = stripe.Charge.list(created={'gte': since}, limit=100)
            total_revenue = sum(c['amount'] for c in charges.data if c['paid']) / 100
            currency = charges.data[0]['currency'].upper() if charges.data else 'USD'

            customers = stripe.Customer.list(created={'gte': since}, limit=100)
            new_customer_count = len(customers.data)

            return {
                'status': 'success',
                'period_days': days,
                'revenue': total_revenue,
                'currency': currency,
                'new_customers': new_customer_count,
                'transactions': len(charges.data),
                'message': f'الدخل في {days} يوم: {total_revenue} {currency} | {new_customer_count} عميل جديد | {len(charges.data)} معاملة'
            }
        except ImportError:
            return {'status': 'error', 'message': 'pip install stripe'}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'revenue': 0}

    return await loop.run_in_executor(None, _fetch)


# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE ANALYTICS 4 — زيارات الموقع
# ──────────────────────────────────────────────────────────────────────────────

async def tool_get_analytics_metrics(days: int = 1) -> Dict[str, Any]:
    """
    اجلب احصائيات Google Analytics 4: الزيارات، المستخدمين، معدل الارتداد.
    days: عدد الايام الماضية (افتراضي 1)
    """
    property_id = os.getenv('GA4_PROPERTY_ID', '')
    service_account = os.getenv('GA4_SERVICE_ACCOUNT_JSON', '')

    if not property_id:
        return {
            'status': 'not_configured',
            'message': 'Google Analytics غير مفعل. اضف GA4_PROPERTY_ID و GA4_SERVICE_ACCOUNT_JSON في .env',
            'sessions': 0, 'users': 0
        }

    loop = asyncio.get_event_loop()

    def _fetch():
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
            import json

            if service_account:
                import tempfile
                sa_data = json.loads(service_account)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(sa_data, f)
                    sa_path = f.name
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = sa_path

            client = BetaAnalyticsDataClient()
            request = RunReportRequest(
                property=f'properties/{property_id}',
                dimensions=[Dimension(name='date')],
                metrics=[
                    Metric(name='sessions'),
                    Metric(name='activeUsers'),
                    Metric(name='bounceRate'),
                    Metric(name='averageSessionDuration'),
                ],
                date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
            )

            response = client.run_report(request)
            sessions = 0
            users = 0
            bounce = 0.0

            for row in response.rows:
                sessions += int(row.metric_values[0].value)
                users += int(row.metric_values[1].value)
                bounce = float(row.metric_values[2].value)

            return {
                'status': 'success',
                'period_days': days,
                'sessions': sessions,
                'users': users,
                'bounce_rate': round(bounce * 100, 1),
                'message': f'الموقع: {sessions} جلسة | {users} مستخدم | معدل الارتداد {round(bounce * 100, 1)}%'
            }
        except ImportError:
            return {'status': 'error', 'message': 'pip install google-analytics-data'}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'sessions': 0, 'users': 0}

    return await loop.run_in_executor(None, _fetch)


# ──────────────────────────────────────────────────────────────────────────────
# INSTAGRAM GRAPH API — متابعون وتفاعل
# ──────────────────────────────────────────────────────────────────────────────

async def tool_get_instagram_metrics() -> Dict[str, Any]:
    """
    اجلب احصائيات Instagram: المتابعون، الوصول، التفاعل.
    """
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
    ig_user_id = os.getenv('INSTAGRAM_USER_ID', '')

    if not access_token or not ig_user_id:
        return {
            'status': 'not_configured',
            'message': 'Instagram غير مفعل. اضف INSTAGRAM_ACCESS_TOKEN و INSTAGRAM_USER_ID في .env',
            'followers': 0
        }

    loop = asyncio.get_event_loop()

    def _fetch():
        try:
            import urllib.request
            import json

            # جلب معلومات الحساب الاساسية
            url = f'https://graph.instagram.com/{ig_user_id}?fields=followers_count,media_count,username&access_token={access_token}'
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())

            followers = data.get('followers_count', 0)
            media_count = data.get('media_count', 0)
            username = data.get('username', '')

            # جلب احصائيات الـ insights
            insights_url = f'https://graph.instagram.com/{ig_user_id}/insights?metric=reach,impressions,profile_views&period=day&access_token={access_token}'
            reach = 0
            impressions = 0
            try:
                with urllib.request.urlopen(insights_url, timeout=10) as resp2:
                    insights_data = json.loads(resp2.read())
                for item in insights_data.get('data', []):
                    if item['name'] == 'reach':
                        reach = item['values'][-1]['value'] if item.get('values') else 0
                    elif item['name'] == 'impressions':
                        impressions = item['values'][-1]['value'] if item.get('values') else 0
            except Exception:
                pass

            return {
                'status': 'success',
                'username': f'@{username}',
                'followers': followers,
                'media_count': media_count,
                'daily_reach': reach,
                'daily_impressions': impressions,
                'message': f'@{username}: {followers:,} متابع | وصول اليوم: {reach:,} | {media_count} منشور'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'followers': 0}

    return await loop.run_in_executor(None, _fetch)


# ──────────────────────────────────────────────────────────────────────────────
# MORNING BRIEFING — تقرير صباحي شامل
# ──────────────────────────────────────────────────────────────────────────────

async def tool_morning_briefing() -> Dict[str, Any]:
    """
    احضر التقرير الصباحي الكامل لسمير: دخل Stripe + زيارات الموقع + Instagram + عدد الايميلات غير المقروءة.
    استخدم هذه الاداة عندما يقول المستخدم 'صباح الخير سمير' او 'ما اخبار اليوم'.
    """
    results = await asyncio.gather(
        tool_get_stripe_metrics(days=1),
        tool_get_analytics_metrics(days=1),
        tool_get_instagram_metrics(),
        return_exceptions=True
    )

    stripe_data = results[0] if not isinstance(results[0], Exception) else {'status': 'error', 'revenue': 0}
    analytics_data = results[1] if not isinstance(results[1], Exception) else {'status': 'error', 'sessions': 0}
    instagram_data = results[2] if not isinstance(results[2], Exception) else {'status': 'error', 'followers': 0}

    now = datetime.now().strftime('%A %d %B %Y — %H:%M')

    briefing_parts = [f'التقرير الصباحي — {now}']

    if stripe_data.get('status') == 'success':
        briefing_parts.append(f"💰 الدخل: {stripe_data['revenue']} {stripe_data.get('currency', '')} | {stripe_data['new_customers']} عميل جديد")
    elif stripe_data.get('status') == 'not_configured':
        briefing_parts.append('💰 Stripe: غير مفعل')

    if analytics_data.get('status') == 'success':
        briefing_parts.append(f"📊 الموقع: {analytics_data['sessions']:,} جلسة | {analytics_data['users']:,} مستخدم")
    elif analytics_data.get('status') == 'not_configured':
        briefing_parts.append('📊 Analytics: غير مفعل')

    if instagram_data.get('status') == 'success':
        briefing_parts.append(f"📱 Instagram: {instagram_data['followers']:,} متابع | وصول {instagram_data.get('daily_reach', 0):,}")
    elif instagram_data.get('status') == 'not_configured':
        briefing_parts.append('📱 Instagram: غير مفعل')

    return {
        'status': 'success',
        'summary': ' | '.join(briefing_parts),
        'briefing': '\n'.join(briefing_parts),
        'stripe': stripe_data,
        'analytics': analytics_data,
        'instagram': instagram_data,
        'message': '\n'.join(briefing_parts),
    }


# ─── Register ─────────────────────────────────────────────────────────────────

tool_registry.register(
    name='morning_briefing',
    func=tool_morning_briefing,
    schema={
        'name': 'morning_briefing',
        'description': 'احضر التقرير الصباحي الكامل: Stripe + Analytics + Instagram. استخدمه عند قول المستخدم صباح الخير او ما اخبار اليوم.',
        'parameters': {'type': 'object', 'properties': {}, 'required': []},
    }
)

tool_registry.register(
    name='get_stripe_metrics',
    func=tool_get_stripe_metrics,
    schema={
        'name': 'get_stripe_metrics',
        'description': 'اجلب احصائيات Stripe: الدخل والعملاء الجدد والمعاملات.',
        'parameters': {
            'type': 'object',
            'properties': {
                'days': {'type': 'integer', 'default': 1, 'description': 'عدد الايام الماضية'}
            },
            'required': [],
        },
    }
)

tool_registry.register(
    name='get_analytics_metrics',
    func=tool_get_analytics_metrics,
    schema={
        'name': 'get_analytics_metrics',
        'description': 'اجلب احصائيات Google Analytics 4: الزيارات والمستخدمين ومعدل الارتداد.',
        'parameters': {
            'type': 'object',
            'properties': {
                'days': {'type': 'integer', 'default': 1}
            },
            'required': [],
        },
    }
)

tool_registry.register(
    name='get_instagram_metrics',
    func=tool_get_instagram_metrics,
    schema={
        'name': 'get_instagram_metrics',
        'description': 'اجلب احصائيات Instagram: عدد المتابعين والوصول والتفاعل.',
        'parameters': {'type': 'object', 'properties': {}, 'required': []},
    }
)
