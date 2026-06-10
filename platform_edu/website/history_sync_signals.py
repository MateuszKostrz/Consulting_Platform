"""
Django Signals for History SL to HL Auto-Sync

These signals automatically sync History SL essay questions to History HL when:
- A new SL question is created (if sync_to_hl=True)
- An existing SL question is updated (if sync_to_hl=True)
- An SL question is deleted (removes corresponding HL question)
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import History_SL_Questionbank, History_HL_Questionbank
import logging

logger = logging.getLogger(__name__)


def find_corresponding_hl_question(sl_question):
    """Find the corresponding HL question for an SL question"""
    try:
        if sl_question.hl_question_id:
            try:
                return History_HL_Questionbank.objects.get(id=sl_question.hl_question_id)
            except History_HL_Questionbank.DoesNotExist:
                History_SL_Questionbank.objects.filter(id=sl_question.id).update(hl_question_id=None)

        # Fall back to matching by title + chapter
        hl_question = History_HL_Questionbank.objects.filter(
            chapter=sl_question.chapter,
            title=sl_question.title,
        ).first()

        return hl_question
    except Exception as e:
        logger.error(f"Error finding corresponding HL question: {e}")
        return None


def sync_fields(hl_question, sl_question):
    """Copy all shared fields from SL to HL question"""
    hl_question.paper = sl_question.paper
    hl_question.chapter = sl_question.chapter
    hl_question.title = sl_question.title
    hl_question.command_term = sl_question.command_term
    hl_question.explanation = sl_question.explanation
    hl_question.intro = sl_question.intro
    hl_question.body = sl_question.body
    hl_question.conclusion = sl_question.conclusion
    hl_question.difficulty = sl_question.difficulty
    hl_question.marks = sl_question.marks
    hl_question.type = sl_question.type
    hl_question.verified = sl_question.verified
    hl_question.save()


@receiver(post_save, sender=History_SL_Questionbank)
def sync_sl_to_hl_on_save(sender, instance, created, **kwargs):
    """Signal handler: Sync SL essay question to HL when saved"""
    if not instance.sync_to_hl:
        if instance.hl_question_id:
            try:
                History_HL_Questionbank.objects.filter(id=instance.hl_question_id).delete()
                logger.info(f"Deleted HL question {instance.hl_question_id} as SL question {instance.id} sync_to_hl is False")
            except History_HL_Questionbank.DoesNotExist:
                pass
            History_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=None)
        return

    # Only sync chapters that also exist in HL
    hl_chapters = dict(History_HL_Questionbank.CHAPTERS)
    if instance.chapter not in hl_chapters:
        logger.info(f"Skipping sync for SL question {instance.id} - chapter '{instance.chapter}' not in HL")
        return

    try:
        corresponding_hl = find_corresponding_hl_question(instance)

        if corresponding_hl:
            sync_fields(corresponding_hl, instance)
            if instance.hl_question_id != corresponding_hl.id:
                History_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=corresponding_hl.id)
            logger.info(f"Updated HL question {corresponding_hl.id} from SL question {instance.id}")
        else:
            new_hl = History_HL_Questionbank.objects.create(
                paper=instance.paper,
                chapter=instance.chapter,
                title=instance.title,
                command_term=instance.command_term,
                explanation=instance.explanation,
                intro=instance.intro,
                body=instance.body,
                conclusion=instance.conclusion,
                difficulty=instance.difficulty,
                marks=instance.marks,
                type=instance.type,
                verified=instance.verified,
            )
            History_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=new_hl.id)
            logger.info(f"Created new HL question {new_hl.id} from SL question {instance.id}")

    except Exception as e:
        logger.error(f"Error syncing History SL question {instance.id} to HL: {e}")


@receiver(post_delete, sender=History_SL_Questionbank)
def delete_hl_on_sl_delete(sender, instance, **kwargs):
    """Signal handler: Remove corresponding HL question when SL question is deleted"""
    if instance.hl_question_id:
        try:
            History_HL_Questionbank.objects.filter(id=instance.hl_question_id).delete()
            logger.info(f"Deleted corresponding HL question {instance.hl_question_id} for deleted SL question {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting HL question for SL question {instance.id}: {e}")
