from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserAnswer, TopicProgress

@receiver(post_save, sender=UserAnswer)
def update_topic_progress(sender, instance, created, **kwargs):
    if not created:
        return

    topic = instance.question.topic
    if not topic:
        return

    difficulty = instance.question.difficulty  # 'easy', 'medium', 'hard'

    progress, _ = TopicProgress.objects.get_or_create(
        user=instance.user,
        topic=topic
    )

    progress.total_attempted += 1
    if instance.is_correct:
        progress.total_correct += 1

    if difficulty in ('easy', 'medium', 'hard'):
        attempted_field = f"{difficulty}_attempted"
        correct_field = f"{difficulty}_correct"
        
        setattr(progress, attempted_field, getattr(progress, attempted_field) + 1)
        if instance.is_correct:
            setattr(progress, correct_field, getattr(progress, correct_field) + 1)

    progress.save()
