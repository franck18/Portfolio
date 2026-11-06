"""Publish only the leased FrayFit menu labels, with verified atomic rollback."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from hosting import connect
from menu_labels import (NEW_LABEL, ORIGINAL_LABELS, TARGET_HREF,
                         menu_anchor, menu_label_counts)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'evidence/frayfit-menu/manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_remote(sftp, path):
    with sftp.open(path, 'rb') as file:
        return file.read()


def verify(data, expected_hash, expected_size, description):
    if len(data) != expected_size or digest(data) != expected_hash:
        raise RuntimeError('Hash/size verification failed: ' + description)


def load_local_files():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if (manifest.get('schema_version') != 1 or
            manifest.get('remote_root') != 'www' or
            manifest.get('target_href') != TARGET_HREF or
            manifest.get('new_label') != NEW_LABEL):
        raise RuntimeError('Unexpected FrayFit menu lease format.')
    records = manifest['files']
    if not records:
        raise RuntimeError('The FrayFit menu lease is empty.')
    for name, record in records.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or path.as_posix() != name or
                '..' in path.parts or '\\' in name or ':' in name or
                path.suffix != '.html'):
            raise RuntimeError('Unsafe/non-HTML lease path: ' + name)
        for key in ('sha256', 'updated_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', record[key]):
                raise RuntimeError('Invalid hash in lease: ' + name)
        label = record['original_label']
        count = record['replacements']
        if label not in ORIGINAL_LABELS or not isinstance(count, int) or count < 1:
            raise RuntimeError('Unexpected original menu label/count: ' + name)
        data = (ROOT / 'site' / name).read_bytes()
        verify(data, record['updated_sha256'], record['updated_size'],
               'local updated file ' + name)
        if menu_label_counts(data) != {NEW_LABEL: count}:
            raise RuntimeError('Unexpected local navigation labels: ' + name)
        original = data.replace(menu_anchor(NEW_LABEL), menu_anchor(label))
        verify(original, record['sha256'], record['size'],
               'exact label-only change ' + name)
    return records


def save_status(backup, status):
    (backup / 'status.json').write_text(
        json.dumps(status, indent=2) + '\n', encoding='utf-8')


def upload_verified(sftp, source, temporary, expected_hash, expected_size,
                    pending):
    pending.add(temporary)
    sftp.put(str(source), temporary)
    verify(read_remote(sftp, temporary), expected_hash, expected_size, temporary)


def close_connection(client, sftp):
    for connection in (sftp, client):
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def cleanup_temporaries(sftp, pending):
    errors = []
    for temporary in sorted(pending):
        try:
            sftp.remove(temporary)
        except OSError as error:
            if error.errno != 2:
                errors.append(f'{temporary}: {error}')
        except Exception as error:
            errors.append(f'{temporary}: {error}')
    return errors


def rollback(records, attempted, backup, run_id, pending):
    """A fresh connection also handles a dropped upload/rename connection."""
    client = sftp = None
    restored = []
    errors = []
    try:
        client = connect()
        sftp = client.open_sftp()
        for name in reversed(attempted):
            record = records[name]
            remote = 'www/' + name
            temporary = remote + '.frayfit-rollback-' + run_id
            try:
                current = read_remote(sftp, remote)
                if digest(current) == record['sha256']:
                    continue
                verify(current, record['updated_sha256'], record['updated_size'],
                       'rollback target ' + name)
                upload_verified(sftp, backup / name, temporary,
                                record['sha256'], record['size'], pending)
                # Avoid replacing a separate edit made during the upload.
                verify(read_remote(sftp, remote), record['updated_sha256'],
                       record['updated_size'], 'rollback lease ' + name)
                sftp.posix_rename(temporary, remote)
                pending.discard(temporary)
                verify(read_remote(sftp, remote), record['sha256'],
                       record['size'], 'restored file ' + name)
                restored.append(name)
            except Exception as error:
                errors.append(f'{name}: {error}')
        errors.extend(cleanup_temporaries(sftp, pending))
    except Exception as error:
        errors.append('Rollback connection: ' + str(error))
    finally:
        close_connection(client, sftp)
    return restored, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-local', action='store_true',
                        help='Verify exact label-only changes without connecting.')
    arguments = parser.parse_args()
    records = load_local_files()
    count = sum(record['replacements'] for record in records.values())
    print(f'Verified {count} exact menu label changes in {len(records)} local HTML files.',
          flush=True)
    if arguments.check_local:
        return

    client = sftp = None
    pending = set()
    attempted = []
    published = []
    backup = None
    status = {}
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    try:
        client = connect()
        sftp = client.open_sftp()
        # Read and verify the entire remote lease before the first remote write.
        originals = {}
        for name, record in records.items():
            data = read_remote(sftp, 'www/' + name)
            verify(data, record['sha256'], record['size'], 'remote lease ' + name)
            originals[name] = data

        backup = ROOT / 'backups' / ('frayfit-menu-' + run_id)
        backup.mkdir(parents=True, exist_ok=False)
        for name, data in originals.items():
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            verify(target.read_bytes(), records[name]['sha256'],
                   records[name]['size'], 'saved backup ' + name)
        (backup / 'lease.json').write_bytes(MANIFEST.read_bytes())
        status = {'state': 'publishing', 'attempted': attempted,
                  'published': published, 'restored': [], 'rollback_errors': []}
        save_status(backup, status)
        print(f'Verified and backed up all {len(records)} remote files: {backup}',
              flush=True)

        ordered = sorted(records, key=lambda name: (name in ('index.html', 'en/index.html'), name))
        for name in ordered:
            record = records[name]
            remote = 'www/' + name
            temporary = remote + '.frayfit-upload-' + run_id
            upload_verified(sftp, ROOT / 'site' / name, temporary,
                            record['updated_sha256'], record['updated_size'], pending)
            verify(read_remote(sftp, remote), record['sha256'], record['size'],
                   'remote lease immediately before replacement ' + name)
            # Record before rename: a lost acknowledgement may still mean it succeeded.
            attempted.append(name)
            save_status(backup, status)
            sftp.posix_rename(temporary, remote)
            pending.discard(temporary)
            verify(read_remote(sftp, remote), record['updated_sha256'],
                   record['updated_size'], 'published file ' + name)
            published.append(name)
            save_status(backup, status)

        # Confirm the complete result before declaring the publication successful.
        for name, record in records.items():
            verify(read_remote(sftp, 'www/' + name), record['updated_sha256'],
                   record['updated_size'], 'final published file ' + name)
        status['state'] = 'published'
        save_status(backup, status)
        print(f'Published and verified {count} FrayFit menu labels. Backup: {backup}',
              flush=True)
    except Exception as error:
        close_connection(client, sftp)
        client = sftp = None
        if attempted or pending:
            restored, rollback_errors = rollback(
                records, attempted, backup, run_id, pending)
            status.update(state='rollback_failed' if rollback_errors else 'rolled_back',
                          restored=restored, rollback_errors=rollback_errors,
                          failure=str(error))
            save_status(backup, status)
            if rollback_errors:
                raise RuntimeError(
                    f'Publication failed; rollback needs attention. Backups and details: {backup}') from error
            print(f'Publication failed; restored {len(restored)} replaced files. Backup: {backup}',
                  flush=True)
        raise
    finally:
        close_connection(client, sftp)


if __name__ == '__main__':
    main()
