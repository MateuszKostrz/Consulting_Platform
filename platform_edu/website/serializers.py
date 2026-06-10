# serializers.py
from rest_framework import serializers
from .models import Math_AI_SL_Questionbank, Math_AI_HL_Questionbank, Math_AA_SL_Questionbank, Math_AA_HL_Questionbank, Math_AA_HL_Questionbank_Backup, Biology_SL_Questionbank, Biology_HL_Questionbank, Physics_SL_Questionbank, Physics_HL_Questionbank, Comp_Sci_SL_Questionbank, Comp_Sci_HL_Questionbank, Chemistry_SL_Questionbank, Chemistry_HL_Questionbank, History_SL_Questionbank, History_HL_Questionbank

class Math_AI_SL_QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Math_AI_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'chapter2', 'chapter3', 'marks', 'type', 'sync_to_hl', 'hl_question_id']
        # fields = '__all__'



class Math_AI_HL_QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Math_AI_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'chapter2', 'chapter3', 'marks', 'type']


class Math_AA_SL_QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Math_AA_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'chapter2', 'chapter3', 'marks', 'type', 'sync_to_hl', 'hl_question_id']


class Math_AA_HL_QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Math_AA_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'chapter2', 'chapter3', 'marks', 'type']

class Math_AA_HL_Backup_QuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Math_AA_HL_Questionbank_Backup
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type']

class Biology_SL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biology_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer', 'sync_to_hl', 'hl_question_id']

class Biology_HL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biology_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer']


class Physics_SL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Physics_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer', 'sync_to_hl', 'hl_question_id']

class Physics_HL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Physics_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer']

class Comp_Sci_SL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comp_Sci_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type']

class Comp_Sci_HL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comp_Sci_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type']

class Chemistry_SL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemistry_SL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer', 'sync_to_hl', 'hl_question_id']

class Chemistry_HL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemistry_HL_Questionbank
        fields = ['id', 'question', 'answer', 'difficulty', 'paper', 'video', 'chapter', 'marks', 'type', 'correct_answer']

class History_SL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = History_SL_Questionbank
        fields = ['id', 'title', 'command_term', 'explanation', 'intro', 'body', 'conclusion', 'difficulty', 'paper', 'chapter', 'marks', 'type']

class History_HL_QuestionbankSerializer(serializers.ModelSerializer):
    class Meta:
        model = History_HL_Questionbank
        fields = ['id', 'title', 'command_term', 'explanation', 'intro', 'body', 'conclusion', 'difficulty', 'paper', 'chapter', 'marks', 'type']
