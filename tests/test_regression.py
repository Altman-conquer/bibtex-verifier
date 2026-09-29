"""Regression checks for misleading API failures and real-world author formats."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bibtex_verifier.apis import (
    ApiRequestError,
    datacite_by_doi,
    datacite_extract,
    extract_first_author_lastname,
    http_get,
    oa_search,
)
from bibtex_verifier.cli import app
from bibtex_verifier.comparator import compare_entry
from bibtex_verifier.report import build_markdown_report


def test_http_failure_is_distinct_from_absent_record():
    def http_error(status):
        return urllib.error.HTTPError('https://api.openalex.org/works', status, 'error', {}, io.BytesIO())

    with patch('bibtex_verifier.apis.urllib.request.urlopen', side_effect=http_error(429)), patch('bibtex_verifier.apis.time.sleep') as sleep:
        with pytest.raises(ApiRequestError, match='429'):
            http_get('https://api.openalex.org/works')
        assert sleep.call_count == 2
    with patch('bibtex_verifier.apis.urllib.request.urlopen', side_effect=http_error(404)):
        assert http_get('https://api.crossref.org/works/doi') is None
    with patch('bibtex_verifier.apis.urllib.request.urlopen', side_effect=http_error(400)) as get:
        with pytest.raises(ApiRequestError, match='400'):
            http_get('https://api.openalex.org/works')
        assert get.call_count == 1
    with patch('bibtex_verifier.apis.urllib.request.urlopen', side_effect=TimeoutError('timed out')), patch('bibtex_verifier.apis.time.sleep'):
        with pytest.raises(ApiRequestError, match='timed out'):
            http_get('https://api.openalex.org/works')


def test_http_get_recovers_after_transient_failure():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"results": []}'
    transient = urllib.error.HTTPError('https://api.openalex.org/works', 503, 'error', {}, io.BytesIO())
    with patch('bibtex_verifier.apis.urllib.request.urlopen', side_effect=[transient, response]) as get, patch('bibtex_verifier.apis.time.sleep') as sleep:
        assert http_get('https://api.openalex.org/works') == {'results': []}
    assert get.call_count == 2
    sleep.assert_called_once_with(1)


def test_openalex_key_and_custom_title_threshold(monkeypatch):
    monkeypatch.setenv('OPENALEX_API_KEY', 'dummy-key')
    with patch('bibtex_verifier.apis.http_get', return_value={
        'results': [{'title': 'Attention Is All You Need', 'authorships': []}]
    }) as get:
        assert oa_search('Attention Is All You Need', threshold=100)
        assert get.call_args.kwargs['params']['api_key'] == 'dummy-key'


def test_openalex_search_removes_question_mark():
    with patch('bibtex_verifier.apis.http_get', return_value={'results': []}) as get:
        assert oa_search('Reasoning or memorization? unreliable results') is None
    assert get.call_args.kwargs['params']['search'] == 'reasoning or memorization unreliable results'


def test_real_author_formats_and_team_credit():
    assert extract_first_author_lastname('Pranav Putta\nand\n Samir Rafailov') == 'putta'
    assert extract_first_author_lastname('Cheng, Yuxing') == 'cheng'
    entry = {'ID': 'agentq', 'title': 'Test', 'year': '2025', 'author': 'Pranav Putta\nand\n Samir Rafailov'}
    data = {'title': 'Test', 'year': 2025, 'authors': ['Pranav Putta', 'Samir Rafailov']}
    assert compare_entry(entry, api_data=data, source='openalex', match_score=100)['status'] == 'OK'
    team = {**data, 'authors': ['DeepSeek-AI', 'Pranav Putta', 'Samir Rafailov']}
    assert compare_entry(entry, api_data=team, source='openalex', match_score=100)['status'] == 'WARNING'


def test_datacite_doi_and_unverified_report():
    attrs = {'titles': [{'title': 'Qwen3 Technical Report'}], 'publicationYear': 2025,
             'creators': [{'name': 'Yang, An'}], 'publisher': {'name': 'arXiv'},
             'doi': '10.48550/arxiv.2505.09388'}
    with patch('bibtex_verifier.apis.http_get', return_value={'data': {'attributes': attrs}}) as get:
        assert datacite_extract(datacite_by_doi(attrs['doi']))['authors'] == ['Yang, An']
        assert '10.48550/arxiv.2505.09388' in get.call_args.args[0]
    result = compare_entry({'ID': 'missing', 'title': 'Test'}, api_data=None, source=None,
                           match_score=0, api_errors=['OpenAlex: HTTP 429'])
    assert result['status'] == 'UNVERIFIED'
    report = build_markdown_report([result], bib_filename='sample.bib')
    assert 'OpenAlex: HTTP 429' in report and 'UNVERIFIED) | 1 |' in report


def test_cli_reports_openalex_failure_instead_of_false_not_found(tmp_path):
    bib = tmp_path / 'sample.bib'
    bib.write_text('@article{x, title={A Real Paper}, author={Ann Alice}, year={2025}}')
    with patch('bibtex_verifier.cli.oa_search', side_effect=ApiRequestError('HTTP 429')):
        with patch('bibtex_verifier.cli.time.sleep'):
            result = CliRunner().invoke(app, [str(bib), '--json'])
    assert result.exit_code == 1
    data = json.loads(bib.with_suffix('.report.json').read_text())
    assert data[0]['status'] == 'UNVERIFIED'
    assert 'OpenAlex: HTTP 429' in data[0]['issues'][0]
