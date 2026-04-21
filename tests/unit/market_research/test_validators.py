from hbs_ads.features.market_research.models import InsightCandidate, ResearchBrief
from hbs_ads.features.market_research.taxonomy import ANALYSIS_SCHEMA_VERSION
from hbs_ads.features.market_research.validators import (
    validate_analysis_payload,
    validate_brief,
    validate_insight_candidate,
)


def test_validate_brief_accepts_complete_brief() -> None:
    brief = ResearchBrief(
        brief_id='brief_1',
        research_goal='Understand hook patterns',
        market_scope={'geos': ['US']},
        competitor_scope={'mode': 'broad_market'},
        creative_scope={'asset_types': ['video']},
        analysis_focus=['hook_type'],
        sampling_strategy='recent',
        output_mode='insight_cards',
        review_mode='human',
    )
    assert validate_brief(brief) == []


def test_validate_analysis_payload_rejects_bad_vocab() -> None:
    payload = {
        'schema_version': ANALYSIS_SCHEMA_VERSION,
        'observable': {
            'duration_seconds': 10,
            'aspect_ratio': '9:16',
            'contains_gameplay': True,
            'gameplay_visibility': 'WRONG',
            'creator_presence': 'none',
            'text_overlay_present': True,
            'cta_present': False,
            'visual_notes': 'x',
        },
        'taxonomy_tags': {
            'hook_type': 'unknown',
            'format_type': 'unknown',
            'core_angle': 'unknown',
            'cta_style': 'unknown',
            'funnel_stage_guess': 'unknown',
        },
        'interpretation': {
            'hypothesized_strategy': 'x',
            'why_it_might_work': [],
            'likely_target_player': 'x',
            'competitive_positioning_guess': 'x',
            'novelty_assessment': 'low',
        },
        'evidence': [],
        'quality': {'analysis_confidence': 0.5, 'needs_human_review': True, 'failure_modes': []},
    }
    errors = validate_analysis_payload(payload)
    assert any('gameplay_visibility' in err for err in errors)


def test_validate_insight_candidate_requires_evidence_refs() -> None:
    insight = InsightCandidate(
        insight_candidate_id='ins_1',
        run_id='run_1',
        insight_type='pattern',
        title='Title',
        signal='Signal',
        scope={'geo': ['US']},
        evidence_refs=[],
    )
    errors = validate_insight_candidate(insight)
    assert any('evidence_refs' in err for err in errors)
