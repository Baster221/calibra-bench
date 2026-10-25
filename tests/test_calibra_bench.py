import copy
import itertools
import json
import sys
from fractions import Fraction
import pytest


QUESTIONS = ["Does the notice offer Saturday support?", "Must attendees register before entering?", "Is admission free?"]
REFERENCE = "Support is offered Monday to Friday only, with no weekend support. Attendees must register before entering."
SALT = "a" * 64
OUTCOMES = ["NO", "YES", "UNKNOWN"]


def mock(vm, outcomes=OUTCOMES):
    vm.clear_mocks()
    vm.mock_llm(r"CALIBRA_REFERENCE_V1", json.dumps({"answers": [{"id": i, "outcome": value} for i, value in enumerate(outcomes)]}))


@pytest.fixture
def setup(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.warp("2026-10-25T00:00:00Z")
    direct_vm.sender = direct_alice
    c = direct_deploy("contracts/calibra_bench.py", sdk_version="v0.2.12")
    from genlayer import Address
    addresses = [Address(direct_alice), Address(direct_bob), Address(direct_charlie)]
    digest = c.document_commitment(addresses[0], "round-one", json.dumps(QUESTIONS), REFERENCE, SALT)
    r = c.create("round-one", json.dumps(QUESTIONS), json.dumps([str(p) for p in addresses[1:]]), digest, 60, 60, 60)
    mock(direct_vm)
    return c, r, addresses


def forecast(c, r, vm, participant, values, salt=SALT):
    vm.sender = participant
    digest = c.forecast_commitment(r, participant, json.dumps(values), salt)
    c.commit_forecast(r, digest)


def ready(setup, vm, first=(1000, 9000, 5000), second=(9000, 1000, 0)):
    c, r, addresses = setup
    forecast(c, r, vm, addresses[1], first)
    forecast(c, r, vm, addresses[2], second)
    assert c.advance(r) == "REVEAL"
    for participant, values in zip(addresses[1:], (first, second)):
        vm.sender = participant
        c.reveal_forecast(r, json.dumps(values), SALT)
    assert c.advance(r) == "ANSWER"
    vm.sender = addresses[0]
    c.reveal_reference(r, REFERENCE, SALT)
    return c, r, addresses


def test_sealed_round_exact_scoring_and_result_commitment(setup, direct_vm):
    c, r, addresses = ready(setup, direct_vm)
    c.resolve(r)
    assert direct_vm.run_validator() is True
    obj = c.get_round(r)
    assert obj["phase"] == "SCORED" and obj["scored_questions"] == [0, 1]
    assert [p["squared_error"] for p in obj["leaderboard"]] == [2000000, 162000000]
    assert [p["score_bps"] for p in obj["leaderboard"]] == [9900, 1900]
    assert obj["leaderboard"][0]["participant"] == str(addresses[1])
    assert len(c.result_commitment(r)["digest"]) == 64
    with direct_vm.expect_revert("not ready"):
        c.resolve(r)


@pytest.mark.parametrize("idx,changed", [(0,"YES"),(1,"NO"),(2,"YES"),(2,"NO")])
def test_validator_binds_all_outcomes_including_void_column(setup, direct_vm, idx, changed):
    c, r, _ = ready(setup, direct_vm)
    c.resolve(r)
    values = list(OUTCOMES)
    values[idx] = changed
    mock(direct_vm, values)
    assert direct_vm.run_validator() is False


def test_answer_row_order_is_canonical_not_a_disagreement(setup, direct_vm):
    c, r, _ = ready(setup, direct_vm)
    c.resolve(r)
    rows = [{"id": i, "outcome": value} for i, value in enumerate(OUTCOMES)]
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"CALIBRA_REFERENCE_V1", json.dumps({"answers": rows[::-1]}))
    assert direct_vm.run_validator() is True


def test_all_unknown_voids_the_same_columns_for_everyone(setup, direct_vm):
    c, r, _ = ready(setup, direct_vm)
    mock(direct_vm, ["UNKNOWN"] * 3)
    c.resolve(r)
    assert c.get_round(r)["phase"] == "VOID"
    assert c.get_round(r)["void_reason"] == "ALL_UNKNOWN"
    assert c.get_round(r)["leaderboard"] == []
    with direct_vm.expect_revert("No scored result"):
        c.result_commitment(r)


def test_forecasts_hidden_until_commit_cohort_closes(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    assert c.get_round(r)["players"][0]["probabilities"] == []
    with direct_vm.expect_revert("reveal window closed"):
        c.reveal_forecast(r, '[1000,9000,5000]', SALT)
    with direct_vm.expect_revert("not complete"):
        c.advance(r)


def test_reference_cannot_be_revealed_before_predictions_locked(setup, direct_vm):
    c, r, addresses = setup
    with direct_vm.expect_revert("Reference reveal window closed"):
        c.reveal_reference(r, REFERENCE, SALT)


def test_wrong_forecast_salt_vector_and_replay_fail(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    forecast(c, r, direct_vm, addresses[2], [9000,1000,0])
    with direct_vm.expect_revert("Already committed"):
        c.commit_forecast(r, "b" * 64)
    c.advance(r)
    direct_vm.sender = addresses[1]
    with direct_vm.expect_revert("commitment mismatch"):
        c.reveal_forecast(r, '[1000,9000,5000]', "b" * 64)
    with direct_vm.expect_revert("commitment mismatch"):
        c.reveal_forecast(r, '[1001,9000,5000]', SALT)
    c.reveal_forecast(r, '[1000,9000,5000]', SALT)
    with direct_vm.expect_revert("already revealed"):
        c.reveal_forecast(r, '[1000,9000,5000]', SALT)


def test_exact_commit_deadline_excludes_late_participant(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    direct_vm.warp("2026-10-25T00:01:00Z")
    direct_vm.sender = addresses[2]
    with direct_vm.expect_revert("Commit window closed"):
        c.commit_forecast(r, "b" * 64)
    c.advance(r)
    with direct_vm.expect_revert("Not committed"):
        c.reveal_forecast(r, '[9000,1000,0]', SALT)


def test_nonrevealer_never_receives_a_score(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    forecast(c, r, direct_vm, addresses[2], [9000,1000,0])
    c.advance(r)
    direct_vm.sender = addresses[1]
    c.reveal_forecast(r, '[1000,9000,5000]', SALT)
    with direct_vm.expect_revert("not complete"):
        c.advance(r)
    direct_vm.warp("2026-10-25T00:01:00Z")
    c.advance(r)
    direct_vm.sender = addresses[0]
    c.reveal_reference(r, REFERENCE, SALT)
    c.resolve(r)
    assert len(c.get_round(r)["leaderboard"]) == 1


def test_no_commits_and_no_reveals_void_without_model(setup, direct_vm):
    c, r, _ = setup
    direct_vm.warp("2026-10-25T00:01:00Z")
    assert c.advance(r) == "VOID"
    assert c.get_round(r)["void_reason"] == "NO_COMMITS"


def test_no_reveals_void_without_inventing_scores(setup, direct_vm):
    c,r,a=setup
    forecast(c,r,direct_vm,a[1],[1000,9000,5000])
    forecast(c,r,direct_vm,a[2],[9000,1000,0])
    c.advance(r)
    direct_vm.warp('2026-10-25T00:01:00Z')
    assert c.advance(r)=='VOID'
    assert c.get_round(r)['void_reason']=='NO_REVEALS'
    assert c.get_round(r)['leaderboard']==[]


def test_reference_withholding_has_permissionless_void_exit(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    forecast(c, r, direct_vm, addresses[2], [9000,1000,0])
    c.advance(r)
    for participant in addresses[1:]:
        direct_vm.sender = participant
        values = [1000,9000,5000] if participant == addresses[1] else [9000,1000,0]
        c.reveal_forecast(r, json.dumps(values), SALT)
    c.advance(r)
    direct_vm.warp("2026-10-25T00:01:00Z")
    assert c.advance(r) == "VOID"
    assert c.get_round(r)["void_reason"] == "REFERENCE_WITHHELD"


def test_reference_substitution_and_unauthorized_reveal_are_rejected(setup, direct_vm):
    c, r, addresses = setup
    forecast(c, r, direct_vm, addresses[1], [1000,9000,5000])
    forecast(c, r, direct_vm, addresses[2], [9000,1000,0])
    c.advance(r)
    for participant,values in zip(addresses[1:],([1000,9000,5000],[9000,1000,0])):
        direct_vm.sender = participant
        c.reveal_forecast(r,json.dumps(values),SALT)
    c.advance(r)
    with direct_vm.expect_revert("Only benchmark curator"):
        c.reveal_reference(r,REFERENCE,SALT)
    direct_vm.sender=addresses[0]
    with direct_vm.expect_revert("Reference commitment mismatch"):
        c.reveal_reference(r,REFERENCE+' Admission is free.',SALT)
    assert c.get_round(r)["reference"] == ""


def test_resolution_timeout_at_exact_boundary(setup, direct_vm):
    c,r,_=ready(setup,direct_vm)
    direct_vm.warp("2026-10-25T00:01:00Z")
    with direct_vm.expect_revert("not ready or expired"):
        c.resolve(r)
    assert c.advance(r)=="VOID"
    assert c.get_round(r)["void_reason"]=="CONSENSUS_TIMEOUT"


@pytest.mark.parametrize("values", [[True,1,2],[-1,0,0],[10001,0,0],[0,0],[0.0,0,0]])
def test_probability_schema_is_integer_complete_and_bounded(setup,direct_vm,values):
    c,r,addresses=setup
    with direct_vm.expect_revert("one integer probability"):
        c.forecast_commitment(r,addresses[1],json.dumps(values),SALT)


def test_reference_and_forecast_commitments_bind_domains(setup,direct_vm):
    c,r,a=setup
    original=c.forecast_commitment(r,a[1],'[1,2,3]',SALT)
    assert original != c.forecast_commitment(r,a[2],'[1,2,3]',SALT)
    assert original != c.forecast_commitment(r,a[1],'[1,2,4]',SALT)
    doc=c.document_commitment(a[0],'round-one',json.dumps(QUESTIONS),REFERENCE,SALT)
    assert doc != c.document_commitment(a[0],'different-tag',json.dumps(QUESTIONS),REFERENCE,SALT)


def test_invalid_leader_and_error_disagree(setup,direct_vm):
    c,r,_=ready(setup,direct_vm)
    c.resolve(r)
    assert direct_vm.run_validator(leader_result={"NO":1,"YES":2,"UNKNOWN":3}) is False
    assert direct_vm.run_validator(leader_result=['YES']) is False
    assert direct_vm.run_validator(leader_error=RuntimeError('unavailable')) is False


@pytest.mark.parametrize("bad", [{"answers":[]},{"answers":[{"id":0,"outcome":"YES"}]*3},{"answers":[{"id":True,"outcome":"YES"},{"id":1,"outcome":"YES"},{"id":2,"outcome":"NO"}]}])
def test_malformed_resolution_preserves_ready_state(setup,direct_vm,bad):
    c,r,_=ready(setup,direct_vm)
    before=copy.deepcopy(c.get_round(r))
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r'CALIBRA_REFERENCE_V1',json.dumps(bad))
    with direct_vm.expect_revert('LLM_ERROR'):
        c.resolve(r)
    assert c.get_round(r)==before


def test_exact_error_ties_have_shared_rank(setup,direct_vm):
    c,r,_=ready(setup,direct_vm,first=(1000,9000,0),second=(1000,9000,10000))
    c.resolve(r)
    assert [p['rank'] for p in c.get_round(r)['leaderboard']]==[1,1]


def test_display_rounding_cannot_create_a_ranking_tie(setup):
    module=next(m for m in list(sys.modules.values()) if m is not None and getattr(m,'__name__','').startswith('_contract_calibra_bench'))
    rows=[{'participant':'z','revealed':True,'probabilities':[1]},
          {'participant':'a','revealed':True,'probabilities':[2]}]
    result=module._scores(rows,['NO'])['leaderboard']
    assert [r['score_bps'] for r in result]==[9999,9999]
    assert [r['participant'] for r in result]==['z','a']
    assert [r['rank'] for r in result]==[1,2]


def test_roster_and_tag_cannot_be_reinterpreted_after_creation(setup,direct_vm):
    c,r,a=setup
    direct_vm.sender=a[0]
    digest=c.get_round(r)['reference_digest']
    for roster in ([str(a[0]),str(a[1])],[str(a[1]),str(a[1])]):
        with direct_vm.expect_revert('Curator, zero or duplicate'):
            c.create('new-tag',json.dumps(QUESTIONS),json.dumps(roster),digest,60,60,60)
    with direct_vm.expect_revert('tag already used'):
        c.create('round-one',json.dumps(QUESTIONS),json.dumps([str(x) for x in a[1:]]),digest,60,60,60)


def test_all_27_outcome_vectors_and_probability_grid_match_rational_reference(setup):
    module=next(m for m in list(sys.modules.values()) if m is not None and getattr(m,'__name__','').startswith('_contract_calibra_bench'))
    players=[{'participant':'a','revealed':True,'probabilities':[0,5000,10000]},
             {'participant':'b','revealed':True,'probabilities':[10000,2500,5000]},
             {'participant':'c','revealed':False,'probabilities':[]}]
    for outcomes in itertools.product(('YES','NO','UNKNOWN'),repeat=3):
        actual=module._scores(players,list(outcomes))
        indices=[i for i,x in enumerate(outcomes) if x!='UNKNOWN']
        assert actual['scored_questions']==indices
        if not indices:
            assert actual['leaderboard']==[]
            continue
        expected={}
        for p in players[:2]:
            loss=sum((Fraction(p['probabilities'][i],10000)-(1 if outcomes[i]=='YES' else 0))**2 for i in indices)/len(indices)
            expected[p['participant']]=(1-loss)*10000
        for row in actual['leaderboard']:
            exact=expected[row['participant']]
            assert row['score_bps']==exact.numerator//exact.denominator
    # Exhaustive 5x5 probability grid against both binary outcomes.
    for p,q,y in itertools.product((0,2500,5000,7500,10000),repeat=3):
        if y not in (0,10000):
            continue
        rows=[{'participant':'a','revealed':True,'probabilities':[p]}, {'participant':'b','revealed':True,'probabilities':[q]}]
        actual=module._scores(rows,['YES' if y else 'NO'])['leaderboard']
        assert actual[0]['squared_error']<=actual[1]['squared_error']
