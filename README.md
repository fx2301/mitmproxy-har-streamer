# Setup

1. Install [mitmproxy](https://github.com/mitmproxy/mitmproxy) and configure your browser of choice to work with it.
1. Install [mitmproxy-block-traffic](https://github.com/fx2301/mitmproxy-block-traffic): `git clone git@github.com:fx2301/mitmproxy-block-traffic.git` 
1. Install [har2requests](https://github.com/fx2301/har2requests): `git clone git@github.com:fx2301/har2requests.git` 
1. Install this script: `git clone git@github.com:fx2301/mitmproxy-har-streamer.git`

# Workflow

1. Start up a browser, ensure it's cookie-less, and pointing to your mitmproxy proxy.
1. Begin capturing requests with: `mitmdump -s mitmproxy-block-traffic/block_traffic.py --set allowed_hosts=*.thetargetsite.com -s mitmproxy-har-streamer/stream.py`.
1. Interact with the website in the browser.
1. Exit `mitmdump`.
1. Run analysis to generate a HAR from the significant requests: `python3 analyze.py`.
1. Run `har2requests` to generate an automation script: `har2requests request_stream.har --generate-assertions --exclude-cookie-headers > automation_script.py`
1. Optionally, repeat the above steps and do a `diff` of the resulting scripts to see what the variations are.
