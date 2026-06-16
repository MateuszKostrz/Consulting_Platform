from .constants import DIAGNOSTIC_STAGES
from .models import DiagnosticStage


def ensure_diagnostic_stages(personal_profile):
    existing_keys = set(
        personal_profile.diagnostic_stages.values_list('stage_key', flat=True),
    )
    to_create = []
    for stage_config in DIAGNOSTIC_STAGES:
        if stage_config['key'] in existing_keys:
            continue
        to_create.append(
            DiagnosticStage(
                personal_profile=personal_profile,
                stage_key=stage_config['key'],
                sort_order=stage_config['step'],
            ),
        )
    if to_create:
        DiagnosticStage.objects.bulk_create(to_create)

    return personal_profile.diagnostic_stages.order_by('sort_order', 'stage_key')


def get_diagnostic_stage_items(personal_profile):
    ensure_diagnostic_stages(personal_profile)
    stage_map = {
        stage.stage_key: stage
        for stage in personal_profile.diagnostic_stages.all()
    }
    items = []
    for stage_config in DIAGNOSTIC_STAGES:
        items.append({
            'config': stage_config,
            'stage': stage_map[stage_config['key']],
        })
    return items
