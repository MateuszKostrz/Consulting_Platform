from django.core.management.base import BaseCommand
from website.models import Member
import csv

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file')

    def handle(self, *args, **kwargs):
        columns = Member.using('custom_db')._meta.fields
        column_names = [field.name for field in columns]
        print("Columns in the Member model:", column_names)
