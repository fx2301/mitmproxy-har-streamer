"""
Code fragments reused from from https://raw.githubusercontent.com/mitmproxy/mitmproxy/a51dc10d8b97d46c77d11a4bbb4d0c393b2c8a39/examples/contrib/har_dump.py with license https://github.com/mitmproxy/mitmproxy/blob/a51dc10d8b97d46c77d11a4bbb4d0c393b2c8a39/LICENSE
"""

import base64
import datetime
import glob
import json
import mitmproxy
import mitmproxy.http
import mitmproxy.utils
import mitmproxy.net.http
import os
import os.path

class Streamer:
    def __init__(self):
        self.request_count = 0
        self.record_output = True

    def load(self, l):
        l.add_option(
            "stream_output_directory", str, "./request_stream", "Path to output stream data.",
        )

    def configure(self, updated):
        mitmproxy.ctx.log("Ohai!")
        self.record_output = True
        os.makedirs(mitmproxy.ctx.options.stream_output_directory, exist_ok=True)
        
        if not os.path.isdir(mitmproxy.ctx.options.stream_output_directory):
            mitmproxy.ctx.log(f"Will not stream output as directory was not created: {mitmproxy.ctx.options.stream_output_directory}")
            self.record_output = False
            return

        if len(glob.glob(f'{mitmproxy.ctx.options.stream_output_directory}/request*.json')) > 0:
            mitmproxy.ctx.log(f"Will not stream output to directory as it already contains stream data: {mitmproxy.ctx.options.stream_output_directory}")
            self.record_output = False
            return

    def response(self, flow: mitmproxy.http.HTTPFlow):
        response_body_size = len(flow.response.raw_content) if flow.response.raw_content else 0
        response_body_decoded_size = len(flow.response.content) if flow.response.content else 0
        response_body_compression = response_body_decoded_size - response_body_size

        entry = {
            "request": {
                "method": flow.request.method,
                "url": flow.request.url,
                "httpVersion": flow.request.http_version,
                "cookies": self.format_request_cookies(flow.request.cookies.fields),
                "headers": self.name_value(flow.request.headers),
                "queryString": self.name_value(flow.request.query or {}),
                "headersSize": len(str(flow.request.headers)),
                "bodySize": len(flow.request.content),
            },
            "response": {
                "status": flow.response.status_code,
                "statusText": flow.response.reason,
                "httpVersion": flow.response.http_version,
                "cookies": self.format_response_cookies(flow.response.cookies.fields),
                "headers": self.name_value(flow.response.headers),
                "content": {
                    "size": response_body_size,
                    "compression": response_body_compression,
                    "mimeType": flow.response.headers.get('Content-Type', '')
                },
                "redirectURL": flow.response.headers.get('Location', ''),
                "headersSize": len(str(flow.response.headers)),
                "bodySize": response_body_size,
            },
            "cache": {},
        }

        # Avoid storing very large responses
        if response_body_size < 50*1024:
            # Store binary data as base64
            if mitmproxy.utils.strutils.is_mostly_bin(flow.response.content):
                entry["response"]["content"]["text"] = base64.b64encode(flow.response.content).decode()
                entry["response"]["content"]["encoding"] = "base64"
            else:
                entry["response"]["content"]["text"] = flow.response.get_text(strict=False)

        if flow.request.method in ["POST", "PUT", "PATCH"]:
            params = [
                {"name": a, "value": b}
                for a, b in flow.request.urlencoded_form.items(multi=True)
            ]
            entry["request"]["postData"] = {
                "mimeType": flow.request.headers.get("Content-Type", ""),
                "text": flow.request.get_text(strict=False),
                "params": params
            }

        filename = f'{mitmproxy.ctx.options.stream_output_directory}/request{"%05d" % self.request_count}.json'
        if not self.record_output:
            filename = '<not recorded>'
        
        msg = f"{filename}: {entry['response']['status']}: {entry['request']['method']} {entry['request']['url']}"
        mitmproxy.ctx.log(msg)
        
        if self.record_output:
            with open(filename, 'w') as f:
                json.dump(entry, f, indent=2)
            
            self.request_count += 1

    def format_cookies(self, cookie_list):
        rv = []

        for name, value, attrs in cookie_list:
            cookie_har = {
                "name": name,
                "value": value,
            }

            # HAR only needs some attributes
            for key in ["path", "domain", "comment"]:
                if key in attrs:
                    cookie_har[key] = attrs[key]

            # These keys need to be boolean!
            for key in ["httpOnly", "secure"]:
                cookie_har[key] = bool(key in attrs)

            # Expiration time needs to be formatted
            expire_ts = mitmproxy.net.http.cookies.get_expiration_ts(attrs)
            if expire_ts is not None:
                cookie_har["expires"] = datetime.datetime.fromtimestamp(expire_ts, datetime.timezone.utc).isoformat()

            rv.append(cookie_har)

        return rv

    def format_request_cookies(self, fields):
        return self.format_cookies(mitmproxy.net.http.cookies.group_cookies(fields))

    def format_response_cookies(self, fields):
        return self.format_cookies((c[0], c[1][0], c[1][1]) for c in fields)

    def name_value(self, obj):
        """
            Convert (key, value) pairs to HAR format.
        """
        return [{"name": k, "value": v} for k, v in obj.items()]

addons = [
    Streamer()
]
