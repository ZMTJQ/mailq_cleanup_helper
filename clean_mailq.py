
"""
mailq cleanup helper that is safer than postsuper -d all but more efficient
than manual checks.
"""

from typing import List, Dict, Any
import argparse
import sys
import re


def parse_records(text: str) -> List[Dict[str, Any]]:
    """
    parses queue.txt, which holds output of mailq, into record objects

        Inputs:
            text: text (as string) to parse
        Output:
            a list of record objects -> [{queue_id: id, ...},...]
    """
    records: List[Dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text.strip(), flags=re.MULTILINE)
    for block in blocks:
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        header = lines[0]
        parts = header.split()
        if len(parts) < 3:
            continue
        queue_id = parts[0]
        try:
            size = int(parts[1])
        except ValueError:
            size = parts[1]
        sender = parts[-1]
        # arrival is whatever's between size and sender in the header
        try:
            after_size = header.index(parts[1]) + len(parts[1])
            before_sender = header.rindex(sender)
            arrival = header[after_size:before_sender].strip()
        except (ValueError, IndexError):
            arrival = ' '.join(parts[2:-1])

        recipients: List[str] = []
        reason_lines: List[str] = []
        for ln in lines[1:]:
            s = ln.strip()
            if '@' in s:
                toks = s.split()
                email = next((t for t in reversed(toks) if '@' in t), s)
                recipients.append(email)
            else:
                reason_lines.append(s)

        records.append({
            'queue_id': queue_id,
            'size': size,
            'arrival': arrival,
            'sender': sender,
            'recipients': recipients,
            'reason': '\n'.join(reason_lines),
        })
    return records


def load_spamwords() -> List[str]:
    """
    loads spam words from file; helper for -all flag

        Output:
            a list of spam words
    """
    try:
        with open('spam_words.txt', 'r', encoding='utf-8') as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith('#')]
    except FileNotFoundError:
        return []


def is_match(rec: Dict[str, Any], spamword: str) -> bool:
    """
    returns true if spamword is in record object

        Inputs:
            rec: record object
            spamword: string
        Output:
            true if record contains spam object
    """
    sw = spamword.lower()
    if sw in rec.get('sender', '').lower():
        return True
    for r in rec.get('recipients', []):
        if sw in r.lower():
            return True
    return False


def review_matches(keyword: str, records: List[Dict[str, Any]], max_count: int = 0) -> tuple[List[str], bool]:
    """
    looks for spam word matches in a list of records, asks for user confirmation,
    adds corresponding records to deletion list

        Inputs:
            keyword: spam word to look for
            record: list of records
            max_count: maximum matches we can find
        Output:
            list of record queue ids to be deleted
    """
    approved: List[str] = []
    for rec in records:
        if is_match(rec, keyword):
            print('===============')
            print('Queue ID: ', rec['queue_id'])
            print('Sender:   ', rec.get('sender', ''))
            print('Arrival:  ', rec.get('arrival', ''))
            print('Recipients:', ', '.join(rec.get('recipients', [])))
            if rec.get('reason'):
                print('Reason:   ', rec['reason'])
            ans = input('add to delete q? [Y/n/f] ').strip().lower()
            # treat empty input (Return) as YES
            if ans == '' or ans in ('y', 'yes'):
                approved.append(rec['queue_id'])
                if max_count and len(approved) >= max_count:
                    return approved, False
            elif ans in ('f', 'flush'):
                # flush: stop processing and indicate early exit
                return approved, True
            # otherwise continue
    return approved, False


def review_matches_auto(keyword: str, records: List[Dict[str, Any]], auto_accept: bool = False, max_count: int = 0) -> tuple[List[str], bool]:
    """
    same as review_matches, but doesn't ask for user confirmation
    """
    if auto_accept:
        matches = [rec['queue_id'] for rec in records if is_match(rec, keyword)]
        if max_count and len(matches) > max_count:
            return matches[:max_count], False
        return matches, False
    return review_matches(keyword, records, max_count=max_count)


def main(argv=None) -> None:
    """
    Accepts keyword or -all flag, prints list of `postsuper -d id`
    commands for user to run to clear out junk mail.

    Also accepts --yes flag, which eliminates user confirmation checks.
    Only use this if you're very confident that mail is junk.

    """
    p = argparse.ArgumentParser()
    p.add_argument('keyword', help="spamword or 'all'")
    p.add_argument('-y', '--yes', action='store_true', help='auto accept all matches')
    p.add_argument('--max', type=int, default=0, help='maximum number of approvals to collect (0 = no limit)')
    args = p.parse_args(argv)

    try:
        with open('queue.txt', 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print('queue.txt not found', file=sys.stderr)
        sys.exit(2)

    records = parse_records(text)
    # this can't just be a set bc we want to preserve order
    to_delete: List[str] = []
    flushed = False
    if args.keyword == 'all':
        for sw in load_spamwords():
            ids, flushed_flag = review_matches_auto(sw, records, auto_accept=args.yes, max_count=args.max and max(0, args.max - len(to_delete)))
            to_delete.extend(ids)
            if flushed_flag:
                flushed = True
                break
            if args.max and len(to_delete) >= args.max:
                break
    else:
        ids, flushed = review_matches_auto(args.keyword, records, auto_accept=args.yes, max_count=args.max)
        to_delete = ids

    # if user flushed early, still dedupe and print what we have

    # dedupe while preserving order
    seen = set()
    deduped = []
    for q in to_delete:
        if q not in seen:
            deduped.append(q)
            seen.add(q)

    if not deduped:
        print('No queue IDs approved for deletion.')
        return

    print(f'Approved {len(deduped)} queue IDs')
    print('\nCommands to run:')
    for q in deduped:
        print(f'postsuper -d {q}')


if __name__ == '__main__':
    main()
