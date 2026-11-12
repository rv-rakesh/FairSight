from demo_data import SCENARIOS, run_scenario_session

def test_all_scenarios_run():
    for key in SCENARIOS:
        res = run_scenario_session(key)
        assert 'risk_score' in res
        assert 'risk_level' in res
        assert 'events' in res
        assert 'activity_log' in res
        assert 'debug_frames' in res
        assert len(res['debug_frames']) > 0
        assert 0 <= res['risk_score'] <= 100

def test_honest_candidate_clean():
    res = run_scenario_session('honest_candidate')
    assert res['risk_score'] == 0
    assert res['risk_level'] == 'Low'
    assert len(res['events']) == 0

def test_screen_peeking_medium_high():
    res = run_scenario_session('screen_peeking')
    assert res['risk_score'] >= 30
    assert any(e['type'] == 'frequent_gaze_away' for e in res['events'])

def test_unauthorized_person_high():
    res = run_scenario_session('unauthorized_person')
    assert res['risk_score'] == 60
    assert res['risk_level'] == 'High'
    assert any(e['type'] == 'multiple_faces' for e in res['events'])
