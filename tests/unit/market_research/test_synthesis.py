from hbs_ads.features.market_research.models import CreativeAnalysisResult, ResearchBrief
from hbs_ads.features.market_research.synthesis import synthesize_insights


def test_synthesize_insights_emits_evidence_backed_records() -> None:
    brief = ResearchBrief(
        brief_id='brief_1',
        research_goal='Analyze hooks',
        market_scope={'geos': ['US'], 'platforms': ['meta'], 'date_range': {'start': '2026-04-01', 'end': '2026-04-30'}},
        competitor_scope={'mode': 'broad_market'},
        creative_scope={'asset_types': ['video']},
        analysis_focus=['hook_type'],
        sampling_strategy='recent',
        output_mode='insight_cards',
        review_mode='human',
    )
    analyses = [
        CreativeAnalysisResult(
            analysis_id='analysis_1',
            run_id='run_1',
            asset_id='asset_1',
            taxonomy_tags={'hook_type': 'fail_then_win', 'format_type': 'raw_gameplay'},
            analysis_status='ok',
        ),
        CreativeAnalysisResult(
            analysis_id='analysis_2',
            run_id='run_1',
            asset_id='asset_2',
            taxonomy_tags={'hook_type': 'fail_then_win', 'format_type': 'raw_gameplay'},
            analysis_status='ok',
        ),
    ]
    insights = synthesize_insights(analyses, brief, 'run_1')
    assert insights
    assert all(insight.run_id == 'run_1' for insight in insights)
    assert all(insight.evidence_refs for insight in insights)
