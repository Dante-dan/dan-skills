#!/usr/bin/env python3
"""Read-only structural audit; cannot judge footage, emotion, rhythm or approval."""
import argparse
import json
from pathlib import Path

RELATIONS = {'cause_effect', 'contrast', 'escalation', 'question_answer', 'action_reaction', 'time_ellipsis', 'spatial_context'}

ROLES = {'hook', 'context', 'development', 'evidence', 'reaction', 'payoff', 'transition', 'pause'}


def audit(data):
    errors, warnings = [], []
    def error(code, where):
        errors.append({'code': code, 'where': where})
    def index(name, key):
        out = {}
        for pos, item in enumerate(data.get(name, [])):
            ident = item.get(key)
            if not ident or ident in out:
                error('missing_or_duplicate_id', f'{name}[{pos}].{key}')
            else:
                out[ident] = item
        return out
    sources = index('sources', 'sourceId')
    shots = index('shots', 'shotId')
    if not sources or not shots:
        error('missing_sources_or_shots', 'sources/shots')
    def span(source_id, start, end, where):
        source = sources.get(source_id)
        if source is None:
            error('unknown_source', where)
            return False
        duration = source.get('sourceDurationUs')
        if (type(start) is not int or type(end) is not int or start < 0 or end <= start
                or (isinstance(duration, (int, float)) and end > duration)):
            error('invalid_source_interval', where)
            return False
        return True
    for ident, shot in shots.items():
        span(shot.get('sourceId'), shot.get('sourceInUs'), shot.get('sourceOutUs'), f'shots.{ident}')
    legacy = data.get('schemaVersion', 1) < 2
    missing_records = []
    if legacy:
        warnings.append({'code': 'legacy_v1_partial_story_records', 'where': 'schemaVersion'})
    else:
        events = index('events', 'eventId')
        stories = index('storyCandidates', 'storyId')
        for ident, event in events.items():
            span(event.get('sourceId'), event.get('sourceInUs'), event.get('sourceOutUs'), f'events.{ident}')
            if event.get('claimKind') not in {'observed', 'inference'}:
                error('missing_observation_kind', f'events.{ident}')
        for ident, shot in shots.items():
            for field in ['eventIds', 'roles', 'viewerAddition', 'removalLoss']:
                if not shot.get(field):
                    error('missing_selection_reason', f'shots.{ident}.{field}')
            if set(shot.get('roles', [])) - ROLES:
                error('unknown_shot_role', f'shots.{ident}.roles')
            for event_id in shot.get('eventIds', []):
                if event_id not in events:
                    error('unknown_event', f'shots.{ident}.{event_id}')
                    continue
                event = events[event_id]
                if event.get('sourceId') != shot.get('sourceId'):
                    error('shot_event_source_mismatch', f'shots.{ident}.{event_id}')
                elif (type(event.get('sourceInUs')) is int and type(event.get('sourceOutUs')) is int
                      and type(shot.get('sourceInUs')) is int and type(shot.get('sourceOutUs')) is int
                      and (event['sourceOutUs'] <= shot['sourceInUs'] or event['sourceInUs'] >= shot['sourceOutUs'])):
                    error('shot_event_interval_disjoint', f'shots.{ident}.{event_id}')
            audio = shot.get('audioSelection')
            if audio:
                span(audio.get('sourceId'), audio.get('inUs'), audio.get('outUs'), f'shots.{ident}.audioSelection')
        for ident, story in stories.items():
            for beat in story.get('beats', []):
                for event_id in beat.get('eventIds', []):
                    if event_id not in events:
                        error('unknown_story_event', f'storyCandidates.{ident}.{event_id}')
            for shot_id in story.get('shotIds', []):
                if shot_id not in shots:
                    error('unknown_story_shot', f'storyCandidates.{ident}.{shot_id}')
        selected = stories.get(data.get('selectedStoryId'))
        if not selected:
            error('missing_selected_story', 'selectedStoryId')
        else:
            opening = selected.get('opening', {})
            for field in ['knownContext', 'viewerQuestion', 'withheldInformation', 'payoffShotIds']:
                if not opening.get(field):
                    error('missing_opening_field', f'opening.{field}')
            selected_ids = set(selected.get('shotIds', []))
            for shot_id in opening.get('payoffShotIds', []):
                if shot_id not in shots or shot_id not in selected_ids:
                    error('payoff_not_in_selected_sequence', f'opening.{shot_id}')
        if len(stories) < 2 and not data.get('candidateLimitReason'):
            warnings.append({'code': 'explain_limited_candidates_without_inventing', 'where': 'candidateLimitReason'})
        for pos, relation in enumerate(data.get('relationships', [])):
            where = f'relationships[{pos}]'
            kind, basis = relation.get('kind'), relation.get('basis')
            if kind not in RELATIONS:
                error('unknown_relation_kind', where)
            for field in ['fromShotId', 'toShotId']:
                if relation.get(field) not in shots:
                    error('unknown_relation_shot', f'{where}.{field}')
            required_same_event = kind == 'action_reaction' or (kind == 'cause_effect' and basis != 'documented_causal_link')
            if required_same_event:
                if basis != 'observed_same_event':
                    error('causal_or_reaction_basis_unconfirmed', where)
                endpoints = [shots.get(relation.get(field), {}) for field in ['fromShotId', 'toShotId']]
                groups = [{events[e].get('eventGroupId') for e in shot.get('eventIds', [])
                           if e in events and events[e].get('eventGroupId')} for shot in endpoints]
                if all(groups) and not groups[0].intersection(groups[1]):
                    error('same_event_claim_conflicts_with_event_groups', where)
                elif not all(groups):
                    warnings.append({'code': 'same_event_group_not_recorded', 'where': where})
            elif kind == 'cause_effect' and basis == 'documented_causal_link':
                evidence = relation.get('evidenceEventIds', [])
                if not evidence or not relation.get('factBasis'):
                    error('documented_cause_requires_evidence', where)
                for event_id in evidence:
                    if event_id not in events or events[event_id].get('claimKind') != 'observed':
                        error('causal_evidence_not_observed', where)
        for pos, coverage in enumerate(data.get('coverage', [])):
            source_id = coverage.get('sourceId')
            for channel, allowed_mode in [('visual', 'continuous'), ('audio', 'listened')]:
                item = coverage.get(channel, {})
                valid = []
                for start, end in item.get('rangesUs', []):
                    if span(source_id, start, end, f'coverage[{pos}].{channel}'):
                        valid.append((start, end))
                if item.get('fullyReviewed'):
                    cursor = 0
                    for start, end in sorted(valid):
                        if start > cursor:
                            break
                        cursor = max(cursor, end)
                    duration = sources.get(source_id, {}).get('sourceDurationUs')
                    if item.get('mode') != allowed_mode or not duration or cursor < duration:
                        error('unsupported_full_coverage_claim', f'coverage[{pos}].{channel}')
        # Audio candidates can be selected before listening; disclose the gap, do not invent approval.
        for ident, shot in shots.items():
            audio = shot.get('audioSelection')
            if not audio or type(audio.get('inUs')) is not int or type(audio.get('outUs')) is not int:
                continue
            ranges = []
            for item in data.get('coverage', []):
                if item.get('sourceId') == audio.get('sourceId') and item.get('audio', {}).get('mode') == 'listened':
                    ranges.extend(item['audio'].get('rangesUs', []))
            cursor = audio['inUs']
            for start, end in sorted(ranges):
                if start > cursor:
                    break
                if end > cursor:
                    cursor = end
            if cursor < audio['outUs']:
                warnings.append({'code': 'selected_audio_not_fully_listened', 'where': f'shots.{ident}.audioSelection'})
        for field in ['coverage', 'events', 'storyCandidates', 'selectedStoryId', 'sequenceReview']:
            if not data.get(field):
                missing_records.append(field)
        if not data.get('coverage'):
            warnings.append({'code': 'coverage_not_recorded', 'where': 'coverage'})
        if not data.get('sequenceReview'):
            warnings.append({'code': 'sequence_review_not_recorded', 'where': 'sequenceReview'})
    return {'mechanicalChecks': 'fail' if errors else 'pass',
            'handoffCompleteness': 'legacy' if legacy else ('partial' if missing_records else 'complete'),
            'missingRecords': missing_records, 'mediaReadiness': 'not_checked', 'creativeReview': 'unreviewed',
            'contentAccessed': False, 'approvalGranted': False, 'errors': errors, 'warnings': warnings,
            'limits': 'Checks declared structure only; does not verify claims, footage, sound, creativity, story or user approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.selection.read_text()))
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        result = {'mechanicalChecks': 'fail', 'handoffCompleteness': 'invalid', 'mediaReadiness': 'not_checked',
                  'creativeReview': 'unreviewed', 'approvalGranted': False,
                  'errors': [{'code': 'invalid_input', 'detail': str(exc)}]}
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        if args.output.resolve() == args.selection.resolve():
            parser.error('--output must not overwrite the input selection')
        args.output.write_text(payload)
    print(payload, end='')
    return 1 if result['mechanicalChecks'] == 'fail' else 0


if __name__ == '__main__':
    raise SystemExit(main())
