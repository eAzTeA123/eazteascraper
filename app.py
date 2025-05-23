from flask import Flask, request, Response, stream_with_context, redirect, url_for
import requests
import httpx
from urllib.parse import urlparse, urljoin
app = Flask(__name__)

# Complete header set captured from Chrome/Brave
BROWSER_HEADERS = {
    "accept": "*/*",
    "accept-language": "de-DE,de;q=0.9",
    "accept-encoding": "gzip, deflate, br, zstd",
    "priority": "u=1, i",
    "referer": "https://oha.to/",
    "sec-ch-ua": '"Chromium";v="136", "Brave";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}
AUTO_HEADERS = {
        "origin": "https://oha.to",
        "referer": "https://oha.to/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "de-DE,de;q=0.9",
        "connection": "keep-alive"
    }
def follow_redirect_chain(url: str, max_redirects: int = 10):
    chain = []
    current = url

    # httpx speaks HTTP/2 when http2=True
    with httpx.Client(headers=BROWSER_HEADERS, timeout=10, http2=True) as client:
        for _ in range(max_redirects):
            resp = client.get(current, follow_redirects=False)  # real GET
            link = {
                "url": current,
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
            }
            chain.append(link)

            if resp.status_code in (301, 302, 303, 307, 308):
                nxt = resp.headers.get("location")
                if not nxt:
                    break
                # resolve relative redirects
                current = urljoin(current, nxt)
                continue
            break
    return chain

@app.route('/')
def home():
    return "eazteascraper is running!"

@app.route("/resolve")
def resolve_redirect():
    url = request.args.get("url", "")
    if not urlparse(url).scheme:
        return {"error": "Invalid or missing url"}, 400

    chain = follow_redirect_chain(url)
    last = chain[-1]

    payload = {
        "original_url": url,
        "final_url": last["url"],
        "final_status_code": last["status_code"],
        "redirect_chain": chain,
        "redirect_count": len(chain) - 1,
    }
    return payload, 200 if last["status_code"] < 400 else 502


FORWARD_HEADERS = {
    "Origin": "https://oha.to",
    "Referer": "https://oha.to/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "de-DE,de;q=0.9",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Gpc": "1",
    "DNT": "1",
}

def get_forward_headers():
    """Get headers to forward with additional custom headers if needed"""
    headers = FORWARD_HEADERS.copy()
    # You can add logic here to override headers from the client request
    return headers

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to allow requests from any origin"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Referer, Accept, Content-Type'
    return response

@app.route("/stream")
def stream_playlist():
    playlist_url = request.args.get("url")
    if not playlist_url:
        return "Missing URL", 400

    headers = get_forward_headers()
    
    try:
        # First try with HEAD to check if the URL is accessible
        head_response = requests.head(playlist_url, headers=headers, timeout=5)
        head_response.raise_for_status()
        
        # Then get the actual content
        response = requests.get(playlist_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching playlist: {str(e)}")
        return f"Error fetching playlist: {str(e)}", 502

    # Process the playlist content
    parsed = urlparse(playlist_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/', 1)[0]}/"
    
    def generate():
        for line in response.iter_lines():
            line = line.decode('utf-8').strip()
            if line and not line.startswith('#'):
                if line.endswith('.ts') or line.endswith('.m4s'):
                    absolute_url = urljoin(base_url, line)
                    yield f"/ts?url={absolute_url}\n"
                else:
                    yield f"{line}\n"
            else:
                yield f"{line}\n"

    return Response(
        stream_with_context(generate()),
        content_type=response.headers.get('content-type', 'application/vnd.apple.mpegurl'),
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

@app.route("/ts")
def stream_ts():
    ts_url = request.args.get("url")
    if not ts_url:
        return "Missing .ts URL", 400

    headers = get_forward_headers()

    def generate():
        try:
            with requests.get(ts_url, headers=headers, stream=True, timeout=10) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
        except Exception as e:
            app.logger.error(f"Error streaming TS segment {ts_url}: {str(e)}")
            yield f"-- ERROR loading ts segment: {str(e)} --".encode()

    return Response(
        stream_with_context(generate()),
        content_type="video/MP2T",
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )


@app.route("/autostream")
def auto_stream():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400
    if not urlparse(url).scheme:
        return {"error": "Invalid or missing url"}, 400
    chain = follow_redirect_chain(url)
    last = chain[-1]
    if last["status_code"] >= 400:
        return {"error": "Failed to resolve URL"}, 502
    resolved_url = last["url"]
    return redirect(url_for('stream_playlist', url=resolved_url))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1337, debug=True)
