"""
Django Signals for Math AI SL to HL Auto-Sync

These signals automatically sync Math AI SL questions to Math AI HL when:
- A new SL question is created (if sync_to_hl=True)
- An existing SL question is updated (if sync_to_hl=True)
- An SL question is deleted (removes corresponding HL question)
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Math_AI_SL_Questionbank, Math_AI_HL_Questionbank
import hashlib
import logging

logger = logging.getLogger(__name__)

def get_question_hash(question_text):
    """Create a hash of the question text for finding corresponding questions"""
    cleaned_text = ' '.join(question_text.strip().lower().split())
    return hashlib.md5(cleaned_text.encode()).hexdigest()

def find_corresponding_hl_question(sl_question):
    """Find the corresponding HL question for an SL question"""
    try:
        # First, try to find by stored hl_question_id
        if sl_question.hl_question_id:
            try:
                hl_question = Math_AI_HL_Questionbank.objects.get(id=sl_question.hl_question_id)
                return hl_question
            except Math_AI_HL_Questionbank.DoesNotExist:
                # The linked HL question was deleted, clear the link
                sl_question.hl_question_id = None
                sl_question.save()
        
        # Try to find by exact question text match (check primary chapter)
        hl_question = Math_AI_HL_Questionbank.objects.filter(
            chapter=sl_question.chapter,
            question=sl_question.question
        ).first()
        
        if hl_question:
            return hl_question
        
        # If not found, try by question hash (for slight variations)
        sl_hash = get_question_hash(sl_question.question)
        hl_questions = Math_AI_HL_Questionbank.objects.filter(
            question=sl_question.question
        )
        
        for hl_q in hl_questions:
            if get_question_hash(hl_q.question) == sl_hash:
                return hl_q
        
        return None
    except Exception as e:
        logger.error(f"Error finding corresponding HL question: {e}")
        return None

@receiver(post_save, sender=Math_AI_SL_Questionbank)
def sync_sl_to_hl_on_save(sender, instance, created, **kwargs):
    """
    Signal handler: Sync SL question to HL when saved
    """
    # Only sync if sync_to_hl is True
    if not instance.sync_to_hl:
        if instance.hl_question_id:
            try:
                Math_AI_HL_Questionbank.objects.filter(id=instance.hl_question_id).delete()
                Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=None)
                logger.info(f"Deleted HL question {instance.hl_question_id} as SL question {instance.id} sync_to_hl is False")
            except Math_AI_HL_Questionbank.DoesNotExist:
                Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=None)
                logger.warning(f"HL question {instance.hl_question_id} not found for deletion, clearing link for SL {instance.id}")
        return
    
    # Only sync chapters that exist in both SL and HL
    sl_chapters = dict(Math_AI_SL_Questionbank.CHAPTERS)
    hl_chapters = dict(Math_AI_HL_Questionbank.CHAPTERS)
    
    if instance.chapter not in hl_chapters:
        logger.info(f"Skipping sync for SL question {instance.id} - chapter '{instance.chapter}' doesn't exist in HL")
        return
    
    try:
        # Find if corresponding HL question already exists
        corresponding_hl = find_corresponding_hl_question(instance)
        
        if created:
            # New SL question created
            if corresponding_hl:
                logger.info(f"SL question {instance.id} created, but corresponding HL question already exists")
                # Update existing HL question
                corresponding_hl.question = instance.question
                corresponding_hl.answer = instance.answer
                corresponding_hl.difficulty = instance.difficulty
                corresponding_hl.paper = instance.paper
                corresponding_hl.video = instance.video
                corresponding_hl.chapter = instance.chapter
                corresponding_hl.chapter2 = instance.chapter2
                corresponding_hl.chapter3 = instance.chapter3
                corresponding_hl.marks = instance.marks
                corresponding_hl.type = instance.type
                corresponding_hl.save()
                
                # Store the link in SL question
                if instance.hl_question_id != corresponding_hl.id:
                    instance.hl_question_id = corresponding_hl.id
                    Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=corresponding_hl.id)
                
                logger.info(f"Updated HL question {corresponding_hl.id} from SL question {instance.id}")
            else:
                # Create new HL question
                new_hl_question = Math_AI_HL_Questionbank.objects.create(
                    question=instance.question,
                    answer=instance.answer,
                    difficulty=instance.difficulty,
                    paper=instance.paper,
                    video=instance.video,
                    chapter=instance.chapter,
                    chapter2=instance.chapter2,
                    chapter3=instance.chapter3,
                    marks=instance.marks,
                    type=instance.type
                )
                
                # Store the link in SL question
                instance.hl_question_id = new_hl_question.id
                Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=new_hl_question.id)
                
                logger.info(f"Created new HL question {new_hl_question.id} from SL question {instance.id}")
        else:
            # Existing SL question updated
            if corresponding_hl:
                # Update corresponding HL question
                corresponding_hl.question = instance.question
                corresponding_hl.answer = instance.answer
                corresponding_hl.difficulty = instance.difficulty
                corresponding_hl.paper = instance.paper
                corresponding_hl.video = instance.video
                corresponding_hl.chapter = instance.chapter
                corresponding_hl.chapter2 = instance.chapter2
                corresponding_hl.chapter3 = instance.chapter3
                corresponding_hl.marks = instance.marks
                corresponding_hl.type = instance.type
                corresponding_hl.save()
                
                # Ensure the link is stored
                if instance.hl_question_id != corresponding_hl.id:
                    Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=corresponding_hl.id)
                
                logger.info(f"Updated HL question {corresponding_hl.id} from updated SL question {instance.id}")
            else:
                # SL question was updated but no corresponding HL exists, create one
                new_hl_question = Math_AI_HL_Questionbank.objects.create(
                    question=instance.question,
                    answer=instance.answer,
                    difficulty=instance.difficulty,
                    paper=instance.paper,
                    video=instance.video,
                    chapter=instance.chapter,
                    chapter2=instance.chapter2,
                    chapter3=instance.chapter3,
                    marks=instance.marks,
                    type=instance.type
                )
                
                # Store the link in SL question
                Math_AI_SL_Questionbank.objects.filter(id=instance.id).update(hl_question_id=new_hl_question.id)
                
                logger.info(f"Created new HL question {new_hl_question.id} from updated SL question {instance.id}")
                
    except Exception as e:
        logger.error(f"Error syncing SL question {instance.id} to HL: {e}")

@receiver(post_delete, sender=Math_AI_SL_Questionbank)
def delete_hl_on_sl_delete(sender, instance, **kwargs):
    """
    Signal handler: Remove corresponding HL question when SL question is deleted
    """
    if instance.hl_question_id:
        try:
            Math_AI_HL_Questionbank.objects.filter(id=instance.hl_question_id).delete()
            logger.info(f"Deleted corresponding HL question {instance.hl_question_id} for deleted SL question {instance.id}")
        except Math_AI_HL_Questionbank.DoesNotExist:
            logger.warning(f"HL question {instance.hl_question_id} not found for deletion (SL question {instance.id})")
        except Exception as e:
            logger.error(f"Error deleting corresponding HL question for SL question {instance.id}: {e}")
