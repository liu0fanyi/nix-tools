"""Recipe-only yt-dlp extension: fetch just the Chinese AI subtitle body."""
from yt_dlp.extractor.bilibili import BiliBiliIE as _BiliBiliIE
from yt_dlp.utils import ExtractorError as _ExtractorError, url_or_none as _url_or_none


class _RecipeAIOnlyIE(_BiliBiliIE, plugin_name='recipe_ai_only'):
    def _get_subtitles(self, video_id, cid, aid=None):
        self.to_screen('Recipe AI-only subtitle filter active')
        info = self._download_json(
            'https://api.bilibili.com/x/player/wbi/v2', video_id,
            query={'aid': aid, 'cid': cid} if aid else {'bvid': video_id, 'cid': cid},
            note=f'Extracting AI subtitle info {cid}', headers=self._HEADERS)
        if not isinstance(info, dict) or info.get('code') != 0 or not isinstance(info.get('data'), dict):
            raise _ExtractorError('Platform AI subtitle query failed; retry rather than skip', expected=True)
        data = info['data']
        if data.get('need_login_subtitle'):
            raise _ExtractorError('AI subtitles require login; retry with a valid browser session', expected=True)
        subtitle = data.get('subtitle')
        if not isinstance(subtitle, dict) or not isinstance(subtitle.get('subtitles'), list):
            raise _ExtractorError('Invalid platform subtitle metadata; retry rather than skip', expected=True)
        for track in subtitle['subtitles']:
            if not isinstance(track, dict):
                raise _ExtractorError('Invalid platform subtitle track', expected=True)
            if track.get('lan') != 'ai-zh':
                continue
            url = _url_or_none(self._proto_relative_url(track.get('subtitle_url') or '', 'https:'))
            if not url:
                raise _ExtractorError('AI subtitle URL missing; retry rather than skip', expected=True)
            body = self._download_json(url, video_id, note='Downloading Chinese AI subtitles')
            if not isinstance(body, dict) or not isinstance(body.get('body'), list) or not body['body']:
                raise _ExtractorError('Empty or invalid AI subtitle body', expected=True)
            return {'ai-zh': [{'ext': 'srt', 'data': self.json2srt(body)}]}
        return {}
