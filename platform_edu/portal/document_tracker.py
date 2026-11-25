"""Consultant documents tracker (admin-only grid)."""

from __future__ import annotations

from django.db import transaction

from .constants import DEFAULT_DOCUMENT_TRACKER_COLUMNS
from .models import DocumentTrackerCell, DocumentTrackerColumn, DocumentTrackerRow, PlatformUser
from .notion_document_tracker_seed import NOTION_DOCUMENT_TRACKER_BY_USER_ID


def sync_document_tracker_column_definitions():
    existing = list(DocumentTrackerColumn.objects.order_by('sort_order', 'id'))
    defaults = DEFAULT_DOCUMENT_TRACKER_COLUMNS

    for index, name in enumerate(defaults):
        if index < len(existing):
            column = existing[index]
            updates = []
            if column.name != name:
                column.name = name
                updates.append('name')
            if column.sort_order != index:
                column.sort_order = index
                updates.append('sort_order')
            if updates:
                column.save(update_fields=updates + ['updated_at'])
        else:
            DocumentTrackerColumn.objects.create(name=name, sort_order=index)

    if len(existing) > len(defaults):
        for column in existing[len(defaults) :]:
            DocumentTrackerCell.objects.filter(column=column).delete()
            column.delete()

    return list(DocumentTrackerColumn.objects.order_by('sort_order', 'id'))


def ensure_document_tracker_columns():
    count = DocumentTrackerColumn.objects.count()
    if count == 0:
        created = []
        for index, name in enumerate(DEFAULT_DOCUMENT_TRACKER_COLUMNS):
            created.append(DocumentTrackerColumn.objects.create(name=name, sort_order=index))
        return created
    return list(DocumentTrackerColumn.objects.order_by('sort_order', 'id'))


@transaction.atomic
def add_document_tracker_column(name: str) -> DocumentTrackerColumn:
    label = (name or '').strip()[:120]
    if not label:
        raise ValueError('Column name is required.')
    ensure_document_tracker_columns()
    next_order = (
        DocumentTrackerColumn.objects.order_by('-sort_order').values_list('sort_order', flat=True).first()
    )
    sort_order = (next_order + 1) if next_order is not None else 0
    column = DocumentTrackerColumn.objects.create(name=label, sort_order=sort_order)
    _bulk_ensure_cells([column.id])
    return column


@transaction.atomic
def delete_document_tracker_column(column_id: int) -> str:
    column = DocumentTrackerColumn.objects.filter(pk=column_id).first()
    if not column:
        raise LookupError('Column not found.')
    if DocumentTrackerColumn.objects.count() <= 1:
        raise ValueError('Keep at least one column on the tracker.')
    name = column.name
    DocumentTrackerCell.objects.filter(column=column).delete()
    column.delete()
    return name


def _bulk_ensure_cells(column_ids, default_status='not_sent'):
    if not column_ids:
        return
    row_ids = list(DocumentTrackerRow.objects.values_list('id', flat=True))
    if not row_ids:
        return

    existing_pairs = set(
        DocumentTrackerCell.objects.filter(row_id__in=row_ids, column_id__in=column_ids).values_list(
            'row_id',
            'column_id',
        )
    )
    to_create = [
        DocumentTrackerCell(row_id=row_id, column_id=column_id, status=default_status)
        for row_id in row_ids
        for column_id in column_ids
        if (row_id, column_id) not in existing_pairs
    ]
    if to_create:
        DocumentTrackerCell.objects.bulk_create(to_create, ignore_conflicts=True)


def document_tracker_rows_queryset():
    return (
        DocumentTrackerRow.objects.select_related('student')
        .prefetch_related('cells__column')
        .order_by('sort_order', 'student__first_name', 'student__last_name')
    )


def cells_by_row_column(rows):
    lookup = {}
    for row in rows:
        for cell in row.cells.all():
            lookup[(row.id, cell.column_id)] = cell.status
    return lookup


@transaction.atomic
def sync_all_students_to_document_tracker():
    columns = ensure_document_tracker_columns()
    column_ids = [column.id for column in columns]

    in_tracker = set(DocumentTrackerRow.objects.values_list('student_id', flat=True))
    missing_student_ids = list(
        PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT)
        .exclude(id__in=in_tracker)
        .order_by('first_name', 'last_name', 'id')
        .values_list('id', flat=True)
    )

    if missing_student_ids:
        start_order = DocumentTrackerRow.objects.count()
        DocumentTrackerRow.objects.bulk_create(
            [
                DocumentTrackerRow(student_id=student_id, sort_order=start_order + index)
                for index, student_id in enumerate(missing_student_ids)
            ]
        )
    elif column_ids:
        row_count = DocumentTrackerRow.objects.count()
        if row_count and DocumentTrackerCell.objects.count() >= row_count * len(column_ids):
            return

    _bulk_ensure_cells(column_ids)


def students_available_for_document_tracker():
    in_tracker = set(DocumentTrackerRow.objects.values_list('student_id', flat=True))
    students = PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT).order_by(
        'first_name',
        'last_name',
        'email',
    )
    return [student for student in students if student.id not in in_tracker]


@transaction.atomic
def add_student_to_document_tracker(student: PlatformUser) -> DocumentTrackerRow:
    ensure_document_tracker_columns()
    row, _ = DocumentTrackerRow.objects.get_or_create(
        student=student,
        defaults={'sort_order': DocumentTrackerRow.objects.count()},
    )
    column_ids = list(DocumentTrackerColumn.objects.values_list('id', flat=True))
    _bulk_ensure_cells(column_ids)
    return row


ensure_student_on_document_tracker = add_student_to_document_tracker


@transaction.atomic
def apply_notion_document_tracker_seed():
    """Overwrite cells for students mapped in notion_document_tracker_seed."""
    columns = list(DocumentTrackerColumn.objects.order_by('sort_order', 'id')[:8])
    if len(columns) != 8:
        return 0

    updated = 0
    for student_id, statuses in NOTION_DOCUMENT_TRACKER_BY_USER_ID.items():
        if len(statuses) != len(columns):
            continue
        row = DocumentTrackerRow.objects.filter(student_id=student_id).first()
        if not row:
            continue
        for column, status in zip(columns, statuses):
            DocumentTrackerCell.objects.update_or_create(
                row=row,
                column=column,
                defaults={'status': status},
            )
            updated += 1
    return updated