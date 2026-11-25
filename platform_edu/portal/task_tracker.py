"""Consultant tasks tracker (admin-only grid)."""

from __future__ import annotations

from django.db import transaction

from .constants import DEFAULT_TASK_TRACKER_COLUMNS
from .models import PlatformUser, TaskTrackerCell, TaskTrackerColumn, TaskTrackerRow
from .notion_task_tracker_seed import NOTION_TASK_TRACKER_BY_USER_ID


def sync_task_tracker_column_definitions():
    """Align column names/order with DEFAULT_TASK_TRACKER_COLUMNS; add missing columns."""
    existing = list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))
    defaults = DEFAULT_TASK_TRACKER_COLUMNS

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
            TaskTrackerColumn.objects.create(name=name, sort_order=index)

    if len(existing) > len(defaults):
        for column in existing[len(defaults) :]:
            TaskTrackerCell.objects.filter(column=column).delete()
            column.delete()

    return list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))


def ensure_task_tracker_columns():
    """Seed default columns only when the grid has none; extra columns are kept."""
    count = TaskTrackerColumn.objects.count()
    if count == 0:
        created = []
        for index, name in enumerate(DEFAULT_TASK_TRACKER_COLUMNS):
            created.append(TaskTrackerColumn.objects.create(name=name, sort_order=index))
        return created
    return list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))


@transaction.atomic
def add_task_tracker_column(name: str) -> TaskTrackerColumn:
    label = (name or '').strip()[:120]
    if not label:
        raise ValueError('Column name is required.')
    ensure_task_tracker_columns()
    next_order = (
        TaskTrackerColumn.objects.order_by('-sort_order').values_list('sort_order', flat=True).first()
    )
    sort_order = (next_order + 1) if next_order is not None else 0
    column = TaskTrackerColumn.objects.create(name=label, sort_order=sort_order)
    _bulk_ensure_cells([column.id])
    return column


@transaction.atomic
def delete_task_tracker_column(column_id: int) -> str:
    column = TaskTrackerColumn.objects.filter(pk=column_id).first()
    if not column:
        raise LookupError('Column not found.')
    if TaskTrackerColumn.objects.count() <= 1:
        raise ValueError('Keep at least one column on the tracker.')
    name = column.name
    TaskTrackerCell.objects.filter(column=column).delete()
    column.delete()
    return name


def _bulk_ensure_cells(column_ids):
    """Create only missing (row, column) cells — one query to list gaps, one bulk insert."""
    if not column_ids:
        return
    row_ids = list(TaskTrackerRow.objects.values_list('id', flat=True))
    if not row_ids:
        return

    existing_pairs = set(
        TaskTrackerCell.objects.filter(row_id__in=row_ids, column_id__in=column_ids).values_list(
            'row_id',
            'column_id',
        )
    )
    to_create = [
        TaskTrackerCell(row_id=row_id, column_id=column_id, status='not_started')
        for row_id in row_ids
        for column_id in column_ids
        if (row_id, column_id) not in existing_pairs
    ]
    if to_create:
        TaskTrackerCell.objects.bulk_create(to_create, ignore_conflicts=True)


def task_tracker_rows_queryset():
    return (
        TaskTrackerRow.objects.select_related('student')
        .prefetch_related('cells__column')
        .order_by('sort_order', 'student__first_name', 'student__last_name')
    )


def cells_by_row_column(rows, columns):
    lookup = {}
    for row in rows:
        for cell in row.cells.all():
            lookup[(row.id, cell.column_id)] = cell.status
    return lookup


def get_or_create_row(student: PlatformUser) -> TaskTrackerRow:
    row, created = TaskTrackerRow.objects.get_or_create(
        student=student,
        defaults={'sort_order': TaskTrackerRow.objects.count()},
    )
    column_ids = list(TaskTrackerColumn.objects.values_list('id', flat=True))
    _bulk_ensure_cells_for_rows([row.id], column_ids)
    return row


def _bulk_ensure_cells_for_rows(row_ids, column_ids):
    if not row_ids or not column_ids:
        return
    existing_pairs = set(
        TaskTrackerCell.objects.filter(row_id__in=row_ids, column_id__in=column_ids).values_list(
            'row_id',
            'column_id',
        )
    )
    to_create = [
        TaskTrackerCell(row_id=row_id, column_id=column_id, status='not_started')
        for row_id in row_ids
        for column_id in column_ids
        if (row_id, column_id) not in existing_pairs
    ]
    if to_create:
        TaskTrackerCell.objects.bulk_create(to_create, ignore_conflicts=True)


@transaction.atomic
def add_student_to_tracker(student: PlatformUser) -> TaskTrackerRow:
    ensure_task_tracker_columns()
    return get_or_create_row(student)


ensure_student_on_task_tracker = add_student_to_tracker


@transaction.atomic
def sync_all_students_to_tracker():
    """Add rows for new students and backfill cells only when columns/rows are missing."""
    columns = ensure_task_tracker_columns()
    column_ids = [column.id for column in columns]

    in_tracker = set(TaskTrackerRow.objects.values_list('student_id', flat=True))
    missing_student_ids = list(
        PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT)
        .exclude(id__in=in_tracker)
        .order_by('first_name', 'last_name', 'id')
        .values_list('id', flat=True)
    )

    if missing_student_ids:
        start_order = TaskTrackerRow.objects.count()
        TaskTrackerRow.objects.bulk_create(
            [
                TaskTrackerRow(student_id=student_id, sort_order=start_order + index)
                for index, student_id in enumerate(missing_student_ids)
            ]
        )
    elif column_ids:
        row_count = TaskTrackerRow.objects.count()
        if row_count and TaskTrackerCell.objects.count() >= row_count * len(column_ids):
            return

    _bulk_ensure_cells(column_ids)


def students_available_for_tracker():
    in_tracker = set(TaskTrackerRow.objects.values_list('student_id', flat=True))
    students = PlatformUser.objects.filter(role=PlatformUser.Role.STUDENT).order_by(
        'first_name',
        'last_name',
        'email',
    )
    return [student for student in students if student.id not in in_tracker]


@transaction.atomic
def apply_notion_task_tracker_seed():
    """Overwrite cells for students mapped in notion_task_tracker_seed."""
    columns = list(TaskTrackerColumn.objects.order_by('sort_order', 'id'))
    if len(columns) != 11:
        return 0

    updated = 0
    for student_id, statuses in NOTION_TASK_TRACKER_BY_USER_ID.items():
        if len(statuses) != len(columns):
            continue
        row = TaskTrackerRow.objects.filter(student_id=student_id).first()
        if not row:
            continue
        for column, status in zip(columns, statuses):
            _, created = TaskTrackerCell.objects.update_or_create(
                row=row,
                column=column,
                defaults={'status': status},
            )
            if created:
                updated += 1
            else:
                TaskTrackerCell.objects.filter(row=row, column=column).update(status=status)
                updated += 1
    return updated