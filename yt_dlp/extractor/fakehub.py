from .common import ExtractorError
from .common import InfoExtractor
from ..utils import (
    try_get,
)



class FakeHubIE(InfoExtractor):
    IE_NAME = 'fakehub'
    _VALID_URL = r'https?://(?:[a-z0-9-]+\.)?fakehub\.com/scene/(?P<id>\d+)'

    """ _TESTS = [{
        # Youtube Embeds
        'url': 'https://abcnews.go.com/Entertainment/peter-billingsley-child-actor-christmas-story-hollywood-power/story?id=51286501',
        'info_dict': {
            'id': '51286501',
            'title': "Peter Billingsley: From child actor in 'A Christmas Story' to Hollywood power player",
            'description': 'Billingsley went from a child actor to Hollywood power player.',
        },
        'playlist_count': 5,
    }, {
        'url': 'http://abcnews.go.com/Entertainment/justin-timberlake-performs-stop-feeling-eurovision-2016/story?id=39125818',
        'info_dict': {
            'id': '38897857',
            'ext': 'mp4',
            'title': 'Justin Timberlake Drops Hints For Secret Single',
            'description': 'Lara Spencer reports the buzziest stories of the day in "GMA" Pop News.',
            'upload_date': '20160505',
            'timestamp': 1462442280,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
            # The embedded YouTube video is blocked due to copyright issues
            'playlist_items': '1',
        },
        'add_ie': ['AbcNewsVideo'],
    }, {
        'url': 'http://abcnews.go.com/Technology/exclusive-apple-ceo-tim-cook-iphone-cracking-software/story?id=37173343',
        'only_matching': True,
    }, {
        # inline.type == 'video'
        'url': 'http://abcnews.go.com/Technology/exclusive-apple-ceo-tim-cook-iphone-cracking-software/story?id=37173343',
        'only_matching': True,
    }] """

    def _select_best_format(self, files):
        """Select best file: prefer 1080p AV1, fallback to 1080p H264, then 720p."""
        
        def match(fmt, codec):
            return next(
                (f for f in files if f.get('format') == fmt and f.get('codec') == codec),
                None
            )
        
        def match_fmt(fmt):
            return next(
                (f for f in files if f.get('format') == fmt),
                None
            )
        
        chosen = (
            match('1080p', 'av1')
            or match('1080p', 'h264')
            or match_fmt('1080p')   # any 1080p codec as last resort
            or match_fmt('720p')
            or files[0]             # absolute fallback
        )
        
        return chosen['urls']['view']

    def _real_extract(self, url):
        scene_id = self._match_id(url)
        #webpage = self._download_webpage(url, scene_id)  # don't even need it!

        cookies = self._get_cookies(url)

        #self.to_screen(f'Cookie jar type: {type(cookies)}')
        #self.to_screen(f'Cookie jar contents: {list(cookies)}')

        access_token = cookies.get('access_token_ma').value
        instance_token = cookies.get('instance_token').value

        if not access_token:
            self.raise_login_required('This site requires authentication. E.g. use --cookies-from-browser vivaldi')

        api_url = f'https://site-api.project1service.com/v2/releases/{scene_id}'
        headers = {
            'Authorization': f'{self._get_cookies(url).get("access_token_ma").value}',
            'Instance': f'{self._get_cookies(url).get("instance_token").value}',
            'X-App-Session-Id': f'{self._get_cookies(url).get("app_session_id").value}',
            'Referer': url,
            'Origin': 'https://site-ma.fakehub.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }

        # Print curl equivalent
        #curl_cmd = f"curl -v '{api_url}'"
        #for k, v in headers.items():
        #    curl_cmd += f" \\\n  -H '{k}: {v}'"
        #self.to_screen(f'CURL EQUIVALENT:\n{curl_cmd}')

        data = self._download_json(api_url, scene_id, headers=headers)

        try:
            result = data['result']   # type: ignore
            files = result['videos']['full']['files']
        except KeyError:
            raise ExtractorError(
                'Could not find video files — are you logged in?',
                expected=True,
            )

        hls_url = self._select_best_format(files)

        formats = self._extract_m3u8_formats(
            hls_url, scene_id, ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            headers={
                'Authorization': access_token,
                'Referer': url,
                'Origin': 'https://site-ma.fakehub.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            }
        )

        # Propagate headers to fragment requests
        for f in formats:
            f.setdefault('http_headers', {}).update({
            #    'Authorization': access_token,
                'Referer': url,
                'Origin': 'https://site-ma.fakehub.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            })

        actors = [a['name'] for a in result.get('actors', [])]

        #thumbnail
        thumbnail = try_get(result, lambda x: x['images']['poster']['0']['xx']['urls']['default'])

        return {
            'id': scene_id,
            'title': result['title'],
            'description': result.get('description'),
            'upload_date': result.get('dateReleased', '')[:10].replace('-', ''),  # '20230917'
            'age_limit': 18,  # always 18 for adult content
            'cast': actors,
            'tags': [],  # maybe fill in from JSON
            'formats': formats,
            'thumbnail': thumbnail,
        }
