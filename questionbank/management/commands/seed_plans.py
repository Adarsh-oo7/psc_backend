from django.core.management.base import BaseCommand
from subscriptions.models import Plan

class Command(BaseCommand):
    help = "Seeds the default subscription plans (Free, Pro Monthly, Pro Yearly)"

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Free Tier',
                'slug': 'free',
                'price': 0.00,
                'interval': 'month',
                'user_type': 'student',
                'features': {
                    'feed_limit': 15,
                    'ai_explanations': False,
                    'premium_mock_tests': False,
                    'friends_ranking': False,
                }
            },
            {
                'name': 'Pro Monthly',
                'slug': 'pro-monthly',
                'price': 199.00,
                'interval': 'month',
                'user_type': 'student',
                'features': {
                    'feed_limit': 999999,
                    'ai_explanations': True,
                    'premium_mock_tests': False,
                    'friends_ranking': False,
                }
            },
            {
                'name': 'Pro Yearly',
                'slug': 'pro-yearly',
                'price': 1499.00,
                'interval': 'year',
                'user_type': 'student',
                'features': {
                    'feed_limit': 999999,
                    'ai_explanations': True,
                    'premium_mock_tests': True,
                    'friends_ranking': True,
                }
            }
        ]

        for p_data in plans_data:
            plan, created = Plan.objects.get_or_create(
                slug=p_data['slug'],
                defaults={
                    'name': p_data['name'],
                    'price': p_data['price'],
                    'interval': p_data['interval'],
                    'user_type': p_data['user_type'],
                    'features': p_data['features'],
                    'active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Update existing plan details
                plan.name = p_data['name']
                plan.price = p_data['price']
                plan.interval = p_data['interval']
                plan.user_type = p_data['user_type']
                plan.features = p_data['features']
                plan.save()
                self.stdout.write(self.style.SUCCESS(f"Updated plan: {plan.name}"))

        self.stdout.write(self.style.SUCCESS("Plan seeding complete!"))
