import json
import glob
import sys

INTERESTING_CONTENT_TYPES = set([
    "text/html"
])
if len(sys.argv) > 1:
    folder = sys.argv[1]
else:
    folder = 'request_stream'

request_filenames = sorted(glob.glob(f'{folder}/request*.json'))
request_har = f'{folder}.har'

entries = {}

interesting_filenames = set([])

cookies = {}
for filename in request_filenames:
    with open(filename, 'r') as f:
        entry = json.load(f)

    request_headers = {
        header['name']:header['value']
        for header in entry['request']['headers']
    }

    response_headers = {
        header['name']:header['value']
        for header in entry['response']['headers']
    }

    interesting = False

    previous_cookies = cookies.copy()

    for cookie in entry['response']['cookies']:
        cookie_key = f"{cookie['name']}||{cookie['path']}"

        if cookie['value'] == '' or ('expires' in cookie and cookie['expires'].startswith('1970-01')):
            if cookie_key in cookies:
                del cookies[cookie_key]
        else:
            if cookie_key in cookies:
                if cookie != cookies[cookie_key]:
                    cookies[cookie_key] = cookie
            else:
                cookies[cookie_key] = cookie

    if cookies != previous_cookies:
        interesting = True

    if not interesting:
        if entry['response']['status'] in [302, 304]:
            interested = False
        else:
            content_type = response_headers.get('Content-Type', None)
            request_method = entry['request']['method']
            if request_method == 'GET' and content_type is not None and content_type.split(';')[0] not in INTERESTING_CONTENT_TYPES:
                interesting = False
            else:
                interesting = True
                # print(f"vvv is intersting because (content_type {content_type} method {request_method}")

    if not interesting:
        continue

    msg = f"{filename}: {entry['response']['status']}: {entry['request']['method']} {entry['request']['url']}"
    print(msg)

    if 'queryString' in entry['request']:
        if len(entry['request']['queryString']) > 0:
            print(json.dumps(entry['request']['queryString'], indent=2))
            referer = request_headers.get('Referer', None)
            print(f"# ^^^ referring page was: {referer}")
            
            for param in entry['request']['queryString']:
                accounted_for = False
                for k, entry in entries.items():
                    if 'content' in entry['response']:
                        if 'text' in entry['response']['content']:
                            if param['value'] in entry['response']['content']['text']:
                                print(f"# ^^^ param \"{param['name']}\" is present in {k}")
                                interesting_filenames.add(k)
                                accounted_for = True
                if not accounted_for:
                    print(f"# ^^^ param \"{param['name']}\" not present in previous responses")

    if 'postData' in entry['request']:
        print(json.dumps(entry['request']['postData'], indent=2))
        referer = request_headers.get('Referer', None)
        print(f"# ^^^ referring page was: {referer}")
        
        if 'params' in entry['request']['postData']:
            for param in entry['request']['postData']['params']:
                accounted_for = False
                for k, entry in entries.items():
                    if 'content' in entry['response']:
                        if 'text' in entry['response']['content']:
                            if param['value'] in entry['response']['content']['text']:
                                print(f"# ^^^ param \"{param['name']}\" is present in {k}")
                                interesting_filenames.add(k)
                                accounted_for = True
                if not accounted_for:
                    print(f"# ^^^ param \"{param['name']}\" not present in previous responses")        

    if cookies != previous_cookies:
        interesting = True
        for k, cookie in cookies.items():
            if k not in previous_cookies:
                print(f"\tAdds cookie {cookie['name']}: {cookie['value']}")
            elif previous_cookies[k] != cookie:
                if cookie['value'] == previous_cookies[k]['value']:
                    print(f"\tUpdated cookie details {cookie['name']}: {previous_cookies[k]} -> {cookie}")
                else:
                    print(f"\tUpdates cookie {cookie['name']}: \"{previous_cookies[k]['value']}\" -> \"{cookie['value']}\"")
        for k, cookie in previous_cookies.items():
            if k not in cookies:
                print(f"\tRemoves cookie {cookie['name']}: {cookie['value']}")

    print()

    entries[filename] = entry

    if interesting:
        interesting_filenames.add(filename)

print(f"Outputing {len(interesting_filenames)} requests to {request_har}...")

har = {
    "log": {
        "version": "1.2",
        "creator": {
            "name": "mitmproxy-har-streamer",
            "version": "1.0",
            "comment": "https://github.com/fx2301/mitmproxy-har-streamer"
        },
        "entries": list(map(
            lambda filename: entries[filename],
            sorted(list(interesting_filenames))
        ))
    }
}

with open(request_har, 'w') as f:
    json.dump(har, f, indent=2)