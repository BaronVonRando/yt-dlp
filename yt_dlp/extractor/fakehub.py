from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_iso8601,
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

    def _real_extract(self, url):
        scene_id = self._match_id(url)
        #webpage = self._download_webpage(url, scene_id)  # don't even need it!

        cookies = self._get_cookies(url)

        self.to_screen(f'Cookie jar type: {type(cookies)}')
        self.to_screen(f'Cookie jar contents: {list(cookies)}')

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
        }

        # Print curl equivalent
        curl_cmd = f"curl -v '{api_url}'"
        for k, v in headers.items():
            curl_cmd += f" \\\n  -H '{k}: {v}'"
        self.to_screen(f'CURL EQUIVALENT:\n{curl_cmd}')

        data = self._download_json(api_url, scene_id, headers=headers)

        
        result = data['result']  # now result points to the right level
        files = result['videos']['full']['files']
        
        hls_url = files[0]['urls']['view']

        formats = self._extract_m3u8_formats(
            hls_url, scene_id, ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            headers={
                'Authorization': access_token,
                'Referer': url,
                'Origin': 'https://site-ma.fakehub.com',
            }
        )

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
            'thumbnail': thumbnail
        }
