import json
from pathlib import Path
from jsonschema import Draft6Validator, FormatChecker
from referencing import Registry, Resource
ROOT=Path(__file__).resolve().parents[2]

def test_generated_har_matches_vendored_schema():
    folder=ROOT/'tests/fixtures/har-schema'
    registry=Registry()
    for file in folder.glob('*.json'):
        schema=json.loads(file.read_text())
        registry=registry.with_resource('https://httpcapture.test/schema/'+file.name,Resource.from_contents(schema))
    schema={'$schema':'http://json-schema.org/draft-06/schema#','$ref':'https://httpcapture.test/schema/har.json'}
    validator=Draft6Validator(schema,registry=registry,format_checker=FormatChecker())
    document=json.loads((ROOT/'artifacts/loopback.har').read_text())
    validator.validate(document)
    from base64 import b64decode

    import hashlib
    entries=document['log']['entries']
    expected=json.loads((ROOT/'artifacts/integration-summary.json').read_text())['binarySha256']
    for entry in entries:
        if entry['request']['url'].endswith('/gzip'):
            content=entry['response']['content']
            assert hashlib.sha256(b64decode(content['text'])).hexdigest()==expected
            import gzip
            assert hashlib.sha256(gzip.decompress(b64decode(entry['response']['_httpCaptureRawContent']['text']))).hexdigest()==expected
        if entry['request']['method']=='POST':
            assert entry['request']['postData']['text']=='{"test":true}'
