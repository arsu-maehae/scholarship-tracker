"""Local-only AI tools. Does not publish or mutate the catalogue."""
import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

from gemini_client import AIError
from gemini_extract import extract_candidate
from gemini_preferences import parse_preferences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='command', required=True)
    search = modes.add_parser('search', help='Interpret a request and search the existing catalogue')
    search.add_argument('request')
    extract = modes.add_parser('extract', help='Prepare an unpublished candidate with source evidence')
    extract.add_argument('url')
    extract.add_argument('--source-key', required=True, help='Stable key assigned by the reviewer')
    extract.add_argument('--scheme', required=True, help='Existing scheme slug')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    try:
        if args.command == 'extract':
            result = extract_candidate(args.url, args.source_key, args.scheme)
        else:
            from main import filter_options, list_schemes, search_scholarships
            parsed = parse_preferences(args.request, fields=set(filter_options()['fields']),
                                       schemes={scheme['slug'] for scheme in list_schemes()})
            result = {'scope': 'reviewed local catalogue only', **parsed}
            if parsed['unsupported']:
                result['message'] = 'Search not run: clarify the unsupported or ambiguous preferences.'
            else:
                defaults = dict(q=None, related=None, related_country=None, country=None, degree=None, field=None, include_unknown_fields=False,
                                funding=None, scheme=None, intake_year=None, limit=20, offset=0)
                result['results'] = search_scholarships(**(defaults | parsed['filters']))
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (AIError, ValueError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
