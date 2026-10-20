#!/usr/bin/env python3
"""Compare a stable local file with observed Drive metadata. Never upload/delete."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path


def verify(local, remote, expected_parent):
    local = Path(local).expanduser().resolve(strict=True)
    if not local.is_file():
        raise ValueError('local must be a regular file')
    before = local.stat()
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    with local.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            sha.update(block)
            md5.update(block)
    after = local.stat()
    def identity(stat):
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    errors = []
    if identity(before) != identity(after):
        errors.append('local_changed_during_hash')
    if not remote.get('id'):
        errors.append('missing_remote_id')
    if remote.get('name') != local.name:
        errors.append('remote_name_mismatch')
    if remote.get('trashed') is not False:
        errors.append('remote_not_confirmed_untrashed')
    if expected_parent not in (remote.get('parents') or []):
        errors.append('remote_parent_mismatch')
    try:
        if int(remote['size']) != before.st_size:
            errors.append('remote_size_mismatch')
    except (KeyError, ValueError, TypeError):
        errors.append('missing_remote_size')
    matched = []
    for key, value in [('sha256Checksum', sha.hexdigest()), ('md5Checksum', md5.hexdigest())]:
        if remote.get(key):
            if str(remote[key]).lower() != value:
                errors.append(key + '_mismatch')
            else:
                matched.append(key)
    if not matched:
        errors.append('no_matching_remote_content_hash')
    return {
        'checkedAt': datetime.datetime.now().astimezone().isoformat(),
        'localPath': str(local), 'localBytes': before.st_size,
        'localSha256': sha.hexdigest(), 'localMd5': md5.hexdigest(),
        'localStat': {'device': before.st_dev, 'inode': before.st_ino,
                      'mtimeNs': before.st_mtime_ns, 'ctimeNs': before.st_ctime_ns},
        'remoteId': remote.get('id'), 'remoteVersion': remote.get('version'),
        'remoteModifiedTime': remote.get('modifiedTime'),
        'expectedParent': expected_parent, 'matchedRemoteHashes': matched,
        'contentVerified': not errors, 'errors': errors,
        'localRemovalPerformed': False,
        'scope': 'Content comparison only. Download integrity, final QC, remote evidence provenance and current file stability must be checked separately before authorized local removal.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', required=True)
    parser.add_argument('--remote-metadata', required=True)
    parser.add_argument('--expected-parent', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    if output in {Path(args.local).expanduser().resolve(), Path(args.remote_metadata).expanduser().resolve()}:
        parser.error('output must be distinct from local file and remote evidence')
    report = verify(args.local, json.loads(Path(args.remote_metadata).read_text()), args.expected_parent)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'contentVerified': report['contentVerified'], 'errors': report['errors'], 'report': str(output)}))
    return 0 if report['contentVerified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
