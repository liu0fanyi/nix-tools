"""S3 probes for an owned native-workspace fixture, never production data."""
import base64
import io
import json
import urllib.parse
import zipfile


CAPABILITIES = (
    "image", "pdf", "epub", "archive", "comic", "audio_video", "git",
    "device_api", "music", "writing", "writing_git", "transcription_local",
)


def check(request, workspace, target):
    """Exercise transport independently of optional server processing.

    request is supplied by the fixture owner, after its random node identity
    and authenticated gateway have been verified. No caller-supplied URLs.
    Missing processing remains a cutover blocker, even with working PDF.js.
    """
    assert target["location_id"] == "default"
    report = target["report"]
    assert report["api_version"] == 1
    capabilities = report["capabilities"]
    assert capabilities["core"]["ready"] is True
    unavailable = {}
    for name in CAPABILITIES:
        capability = capabilities[name]
        assert all(isinstance(capability[key], bool) for key in ("compiled", "enabled", "ready"))
        if not capability["ready"]:
            unavailable[name] = capability["reason"]

    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5WQAAAAASUVORK5CYII=")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        output.writestr("META-INF/container.xml", '''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''')
        output.writestr("book.opf", '''<?xml version="1.0"?><package version="3.0" unique-identifier="id" xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">s3-synthetic</dc:identifier><dc:title>S3 EPUB</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-10-07T00:00:00Z</meta></metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>''')
        output.writestr("chapter.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>S3 EPUB</title></head><body><p>S3 EPUB chapter</p></body></html>')
        output.writestr("nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc"><ol><li><a href="chapter.xhtml">Chapter</a></li></ol></nav></body></html>')
    # This payload deliberately tests attachment transport, not video decoding.
    video = b"S3 synthetic video transport bytes; not a playable video\n" * 4
    fixtures = {"S3 附件 %.png": png, "S3 视频 %.mp4": video, "S3 书籍 %.epub": archive.getvalue()}
    listing = json.loads(request("/?json")[1])
    assert isinstance(listing, dict)
    for name, content in fixtures.items():
        path = "/" + urllib.parse.quote(name, safe="")
        assert request(path, content, method="PUT")[0] in {200, 201}
        assert request(path)[1] == content
        status, body, headers = request(path, headers={"Range": "bytes=0-15"})
        assert status == 206 and body == content[:16]
        assert headers["Content-Range"] == f"bytes 0-15/{len(content)}"
        stream = "/tag-api/v1/proxy/stream/default/" + urllib.parse.quote(name, safe="")
        assert request(stream)[1] == content
        assert (workspace / name).read_bytes() == content
    markdown = "![S3 image](<S3 附件 %.png>)\n\n<video controls src=\"S3 视频 %.mp4\"></video>\n"
    assert request("/tag-api/items/text/write", {"path": "S3.md", "location_id": "default",
                    "text": markdown, "create_only": True})[0] == 201
    status, content, _ = request("/tag-api/items/text/read", {"path": "S3.md", "location_id": "default"})
    assert status == 200 and json.loads(content)["text"] == markdown

    pdf_query = urllib.parse.urlencode({"path": "book.pdf", "location_id": "default"})
    image_query = urllib.parse.urlencode({"path": "S3 附件 %.png", "location_id": "default"})
    epub_query = urllib.parse.urlencode({"path": "S3 书籍 %.epub", "location_id": "default"})
    endpoints = {
        "pdf_info": ("/v1/pdf/info?" + pdf_query, None),
        "pdf_render": ("/pdf/render?" + pdf_query + "&page=1", None),
        "pdf_crop": ("/pdf/crop?" + pdf_query + "&page=1", None),
        "preview": ("/media/preview?" + pdf_query, None),
        "cover": ("/media/cover?" + pdf_query, None),
        "thumbnail": ("/thumbnail?" + image_query, None),
        "epub_info": ("/v1/epub/info?" + epub_query, None),
        "epub_page": ("/v1/epub/page?" + epub_query + "&page=1", None),
        "comic_jobs": ("/comics/conversions", None),
        "video_jobs": ("/video/transcodes", None),
        "archive_extract": ("/items/extract", {"path": "S3 书籍 %.epub", "location_id": "default"}),
        "git_file": ("/git/file?path=S3.md", None),
    }
    statuses = {name: request("/tag-api" + path, data)[0] for name, (path, data) in endpoints.items()}
    # The existing fixed core must report lack of processing honestly. A future
    # enabled backend needs actual processing-job tests before S3 can pass.
    if all(capabilities[name]["compiled"] is False for name in CAPABILITIES):
        assert set(statuses.values()) == {404}, statuses
    removable = "/S3%20%E9%99%84%E4%BB%B6%20%25.png"
    assert request(removable, method="DELETE")[0] in {200, 204}
    assert request(removable)[0] == 404
    assert not (workspace / "S3 附件 %.png").exists()
    return {
        "authenticated_file_upload_download_delete": True,
        "unicode_space_percent_paths": True,
        "range_download": True,
        "markdown_attachment_text_persisted": True,
        "image_epub_and_video_attachment_bytes_roundtrip": True,
        "video_playback_tested": False,
        "epub_browser_render_tested": False,
        "processing_capabilities": {name: capabilities[name] for name in CAPABILITIES},
        "unavailable_capabilities": unavailable,
        "processing_endpoint_statuses": statuses,
        "processing_task_execution_tested": False,
        "cutover_ready": False,
        "production_state_read": False,
        "production_changed": False,
    }
